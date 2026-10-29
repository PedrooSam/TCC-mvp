from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_session
from .models import Project, Task

app = FastAPI(title="MVP Gestão de Projetos (multitenant)")


class ProjectIn(BaseModel):
    name: str
    description: str | None = None


class TaskIn(BaseModel):
    title: str
    done: bool = False


class TaskOut(TaskIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int


class ProjectOut(ProjectIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProjectDetail(ProjectOut):
    tasks: list[TaskOut] = []


def _get_or_404(db: Session, model, id: int):
    obj = db.get(model, id)
    if obj is None:
        raise HTTPException(404, f"{model.__name__} não encontrado")
    return obj


# ---- Projects ----
@app.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, db: Session = Depends(get_session)):
    project = Project(**body.model_dump())
    db.add(project)
    db.commit()
    return project


@app.get("/projects", response_model=list[ProjectOut])
def list_projects(limit: int = 100, offset: int = 0, db: Session = Depends(get_session)):
    return db.scalars(select(Project).order_by(Project.id).limit(limit).offset(offset)).all()


@app.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_session)):
    return _get_or_404(db, Project, project_id)


@app.put("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectIn, db: Session = Depends(get_session)):
    project = _get_or_404(db, Project, project_id)
    for k, v in body.model_dump().items():
        setattr(project, k, v)
    db.commit()
    return project


@app.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_session)):
    db.delete(_get_or_404(db, Project, project_id))
    db.commit()


# ---- Tasks ----
@app.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=201)
def create_task(project_id: int, body: TaskIn, db: Session = Depends(get_session)):
    _get_or_404(db, Project, project_id)
    task = Task(project_id=project_id, **body.model_dump())
    db.add(task)
    db.commit()
    return task


@app.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(project_id: int, limit: int = 100, offset: int = 0, db: Session = Depends(get_session)):
    _get_or_404(db, Project, project_id)
    stmt = select(Task).where(Task.project_id == project_id).order_by(Task.id).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_session)):
    return _get_or_404(db, Task, task_id)


@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskIn, db: Session = Depends(get_session)):
    task = _get_or_404(db, Task, task_id)
    for k, v in body.model_dump().items():
        setattr(task, k, v)
    db.commit()
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_session)):
    db.delete(_get_or_404(db, Task, task_id))
    db.commit()
