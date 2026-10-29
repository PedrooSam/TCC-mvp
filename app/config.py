import os

# database | schema | shared
STRATEGY = os.getenv("TENANT_STRATEGY", "shared")
# Banco "base": usado direto em schema/shared e como referência (host/credenciais) em database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/app")
POOL_SIZE = int(os.getenv("POOL_SIZE", "5"))

assert STRATEGY in ("database", "schema", "shared"), f"TENANT_STRATEGY inválida: {STRATEGY}"
