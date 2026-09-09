from uuid import UUID

from app.domain.models import Workflow, WorkflowEdge, WorkflowNode
from app.domain.workflow import node_definitions_payload
from app.repositories.workflow_repository import WorkflowRepository

from .workflow_validation import WorkflowValidator


class WorkflowService:
    def __init__(
        self,
        workflows: WorkflowRepository,
        validator: WorkflowValidator | None = None,
    ) -> None:
        self.workflows = workflows
        self.validator = validator or WorkflowValidator()

    def list_workflows(self, project_id: UUID) -> list[Workflow]:
        return self.workflows.list_for_project(project_id)

    def create_workflow(
        self,
        project_id: UUID,
        *,
        name: str,
        nodes: list[WorkflowNode],
        edges: list[WorkflowEdge],
    ) -> Workflow:
        workflow = Workflow(
            project_id=project_id,
            name=name.strip(),
            nodes=nodes,
            edges=edges,
        )
        self.validator.validate(workflow)
        return self.workflows.create(project_id, workflow)

    def get_workflow(self, project_id: UUID, workflow_id: UUID) -> Workflow:
        return self.workflows.get(project_id, workflow_id)

    def update_workflow(
        self,
        project_id: UUID,
        workflow_id: UUID,
        *,
        name: str,
        nodes: list[WorkflowNode],
        edges: list[WorkflowEdge],
    ) -> Workflow:
        current = self.workflows.get(project_id, workflow_id)
        workflow = Workflow(
            id=current.id,
            project_id=current.project_id,
            name=name.strip(),
            nodes=nodes,
            edges=edges,
            created_at=current.created_at,
        )
        self.validator.validate(workflow)
        return self.workflows.save(project_id, workflow)

    def delete_workflow(self, project_id: UUID, workflow_id: UUID) -> None:
        self.workflows.delete(project_id, workflow_id)

    def node_definitions(self) -> list[dict]:
        return node_definitions_payload()
