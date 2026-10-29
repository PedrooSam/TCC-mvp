"""Único ponto da aplicação que diferencia as 3 estratégias de multitenancy."""
import re
import threading

from fastapi import Header, HTTPException
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, with_loader_criteria

from .config import DATABASE_URL, POOL_SIZE, STRATEGY
from .models import Base, TenantMixin

_base_url = make_url(DATABASE_URL)
_engines: dict[str, object] = {}  # chave -> engine (ou "visão" da engine) já provisionado
_lock = threading.Lock()


def _new_engine(url):
    return create_engine(url, pool_size=POOL_SIZE, max_overflow=0)


def _provision(tenant: str):
    """Cria (se necessário) o recurso do tenant e devolve a engine a ser usada nas requisições."""
    name = f"tenant_{tenant}"
    if STRATEGY == "database":
        admin = create_engine(_base_url, isolation_level="AUTOCOMMIT")
        with admin.connect() as c:
            if not c.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}):
                c.execute(text(f'CREATE DATABASE "{name}"'))
        admin.dispose()
        engine = _new_engine(_base_url.set(database=name))
        Base.metadata.create_all(engine)
        return engine

    base = _engines.get("_base") or _engines.setdefault("_base", _new_engine(_base_url))
    if STRATEGY == "schema":
        with base.begin() as c:
            c.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{name}"'))
        # Mesma pool/conexões; as tabelas (sem schema) são traduzidas para o schema do tenant.
        engine = base.execution_options(schema_translate_map={None: name})
        Base.metadata.create_all(engine)
        return engine

    Base.metadata.create_all(base)  # shared
    return base


def get_session(x_tenant_id: str = Header(...)):
    if not re.fullmatch(r"[a-z0-9_]{1,32}", x_tenant_id):
        raise HTTPException(400, "X-Tenant-ID inválido (use [a-z0-9_], até 32 caracteres)")
    key = "shared" if STRATEGY == "shared" else x_tenant_id
    engine = _engines.get(key)
    if engine is None:
        with _lock:
            engine = _engines.get(key) or _engines.setdefault(key, _provision(x_tenant_id))
    with Session(engine, info={"tenant_id": x_tenant_id}) as session:
        yield session


if STRATEGY == "shared":
    # Filtro automático por tenant_id em todo SELECT ORM e preenchimento do tenant_id nos INSERTs.
    @event.listens_for(Session, "do_orm_execute")
    def _filter_by_tenant(state):
        if state.is_select and not state.is_column_load:
            tenant = state.session.info["tenant_id"]
            state.statement = state.statement.options(
                with_loader_criteria(TenantMixin, lambda cls: cls.tenant_id == tenant, include_aliases=True)
            )

    @event.listens_for(Session, "before_flush")
    def _stamp_tenant(session, flush_context, instances):
        for obj in session.new:
            obj.tenant_id = session.info["tenant_id"]
