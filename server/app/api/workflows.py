from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.models import Workflow, WorkflowEdge, WorkflowNode, WorkflowPosition
from app.services.errors import ServiceValidationError
from app.services.workflow_service import WorkflowService

from .dependencies import get_workflow_service

router = APIRouter(
    prefix="/projects/{project_id}/workflows",
    tags=["workflows"],
)

definitions_router = APIRouter(tags=["workflows"])


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WorkflowNodeInput(StrictRequest):
    id: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=120)
    version: int = Field(default=1, ge=1)
    position: WorkflowPosition = Field(default_factory=WorkflowPosition)
    connector_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdgeInput(StrictRequest):
    id: str = Field(min_length=1, max_length=120)
    source_node_id: str = Field(min_length=1, max_length=120)
    source_port: str = Field(min_length=1, max_length=120)
    target_node_id: str = Field(min_length=1, max_length=120)
    target_port: str = Field(min_length=1, max_length=120)


class WorkflowCreate(StrictRequest):
    schema_version: int | None = Field(default=None, ge=1)
    id: UUID | None = None
    project_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    nodes: list[WorkflowNodeInput] = Field(default_factory=list)
    edges: list[WorkflowEdgeInput] = Field(default_factory=list)


class WorkflowUpdate(StrictRequest):
    schema_version: int | None = Field(default=None, ge=1)
    id: UUID | None = None
    project_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    nodes: list[WorkflowNodeInput] = Field(default_factory=list)
    edges: list[WorkflowEdgeInput] = Field(default_factory=list)


WorkflowServiceDependency = Annotated[
    WorkflowService, Depends(get_workflow_service)
]


def _nodes(payload_nodes: list[WorkflowNodeInput]) -> list[WorkflowNode]:
    try:
        return [
            WorkflowNode(
                id=node.id,
                type=node.type,
                version=node.version,
                position=node.position,
                connector_id=node.connector_id,
                parameters=node.parameters,
            )
            for node in payload_nodes
        ]
    except ValidationError as error:
        raise ServiceValidationError(str(error)) from error


def _edges(payload_edges: list[WorkflowEdgeInput]) -> list[WorkflowEdge]:
    try:
        return [
            WorkflowEdge(
                id=edge.id,
                source_node_id=edge.source_node_id,
                source_port=edge.source_port,
                target_node_id=edge.target_node_id,
                target_port=edge.target_port,
            )
            for edge in payload_edges
        ]
    except ValidationError as error:
        raise ServiceValidationError(str(error)) from error


@router.get("", response_model=list[Workflow])
def list_workflows(
    project_id: UUID,
    service: WorkflowServiceDependency,
) -> list[Workflow]:
    return service.list_workflows(project_id)


@router.post("", response_model=Workflow, status_code=status.HTTP_201_CREATED)
def create_workflow(
    project_id: UUID,
    payload: WorkflowCreate,
    service: WorkflowServiceDependency,
) -> Workflow:
    return service.create_workflow(
        project_id,
        name=payload.name,
        nodes=_nodes(payload.nodes),
        edges=_edges(payload.edges),
    )


@router.get("/{workflow_id}", response_model=Workflow)
def get_workflow(
    project_id: UUID,
    workflow_id: UUID,
    service: WorkflowServiceDependency,
) -> Workflow:
    return service.get_workflow(project_id, workflow_id)


@router.put("/{workflow_id}", response_model=Workflow)
def update_workflow(
    project_id: UUID,
    workflow_id: UUID,
    payload: WorkflowUpdate,
    service: WorkflowServiceDependency,
) -> Workflow:
    return service.update_workflow(
        project_id,
        workflow_id,
        name=payload.name,
        nodes=_nodes(payload.nodes),
        edges=_edges(payload.edges),
    )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    project_id: UUID,
    workflow_id: UUID,
    service: WorkflowServiceDependency,
) -> None:
    service.delete_workflow(project_id, workflow_id)


@definitions_router.get("/workflow-node-definitions")
def workflow_node_definitions(
    service: WorkflowServiceDependency,
) -> list[dict]:
    return service.node_definitions()
