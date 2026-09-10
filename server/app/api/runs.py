from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from pydantic import BaseModel, ConfigDict

from app.domain.models import WorkflowRun
from app.services.run_service import RunService

from .dependencies import get_run_service

router = APIRouter(tags=["runs"])


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_id: UUID
    character_id: UUID | None = None
    background: bool = False


RunServiceDependency = Annotated[RunService, Depends(get_run_service)]


@router.post(
    "/projects/{project_id}/workflow-runs",
    response_model=WorkflowRun,
    status_code=status.HTTP_201_CREATED,
)
def create_run(
    project_id: UUID,
    payload: RunCreate,
    background_tasks: BackgroundTasks,
    service: RunServiceDependency,
) -> WorkflowRun:
    if payload.background:
        run = service.create_queued_run(
            project_id,
            workflow_id=payload.workflow_id,
            character_id=payload.character_id,
        )
        background_tasks.add_task(service.execute_run, project_id, run.id)
        return run
    return service.create_run(
        project_id,
        workflow_id=payload.workflow_id,
        character_id=payload.character_id,
    )


@router.get("/workflow-runs/{run_id}", response_model=WorkflowRun)
def get_run(run_id: UUID, service: RunServiceDependency) -> WorkflowRun:
    return service.get_run_by_id(run_id)
