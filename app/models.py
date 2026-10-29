from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import STRATEGY


class Base(DeclarativeBase):
    pass


class TenantMixin:
    # A coluna só existe na estratégia "shared"; nas demais o isolamento é físico/lógico no banco.
    if STRATEGY == "shared":
        tenant_id = mapped_column(String(32), index=True)


class Project(TenantMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(500))
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", passive_deletes=True)


class Task(TenantMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(default=False)
    project: Mapped[Project] = relationship(back_populates="tasks")
