import json
import shutil
from uuid import uuid4

import pytest

from app.domain.models import Workflow, WorkflowEdge, WorkflowNode
from app.repositories.errors import ConflictError, NotFoundError
from app.repositories.project_repository import ProjectRepository
from app.repositories.workflow_repository import WorkflowRepository


def _node(node_id: str, node_type: str, **kwargs) -> WorkflowNode:
    return WorkflowNode(id=node_id, type=node_type, **kwargs)


def _workflow(project_id) -> Workflow:
    return Workflow(
        project_id=project_id,
        name="Generation",
        nodes=[
            _node("input", "character_input"),
            _node("prompt", "prompt_variant"),
            _node(
                "generate",
                "image_generation",
                connector_id="mock-generation",
            ),
            _node("results", "result_set"),
        ],
        edges=[
            WorkflowEdge(
                id="e1",
                source_node_id="input",
                source_port="character",
                target_node_id="prompt",
                target_port="character",
            ),
            WorkflowEdge(
                id="e2",
                source_node_id="prompt",
                source_port="prompt",
                target_node_id="generate",
                target_port="prompt",
            ),
            WorkflowEdge(
                id="e3",
                source_node_id="generate",
                source_port="image",
                target_node_id="results",
                target_port="image",
            ),
        ],
    )


def test_workflow_round_trip_without_loss(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    project = projects.create("Circus")
    workflows = WorkflowRepository(tmp_path)
    workflow = _workflow(project.id)

    created = workflows.create(project.id, workflow)
    reloaded = workflows.get(project.id, created.id)

    assert reloaded == created
    assert reloaded.model_dump(mode="json") == created.model_dump(mode="json")


def test_workflow_list_get_save_and_delete(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    project = projects.create("Circus")
    workflows = WorkflowRepository(tmp_path)
    workflow = _workflow(project.id)

    created = workflows.create(project.id, workflow)
    assert [item.id for item in workflows.list_for_project(project.id)] == [created.id]

    updated = created.model_copy(update={"name": "Generation v2"})
    saved = workflows.save(project.id, updated)
    assert saved.name == "Generation v2"
    assert workflows.get(project.id, created.id).name == "Generation v2"

    workflows.delete(project.id, created.id)
    assert workflows.list_for_project(project.id) == []
    with pytest.raises(NotFoundError):
        workflows.get(project.id, created.id)


def test_workflow_identity_cannot_be_changed_by_save(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    project = projects.create("Circus")
    workflows = WorkflowRepository(tmp_path)
    workflow = _workflow(project.id)
    created = workflows.create(project.id, workflow)

    tampered = created.model_copy(update={"project_id": uuid4()})

    with pytest.raises(ConflictError, match="identity"):
        workflows.save(project.id, tampered)


def test_workflow_survives_project_root_move(tmp_path) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    projects = ProjectRepository(source_root)
    workflows = WorkflowRepository(source_root)
    project = projects.create("Circus")
    created = workflows.create(project.id, _workflow(project.id))

    shutil.copytree(source_root, target_root)
    moved = WorkflowRepository(target_root).get(project.id, created.id)

    assert moved == created


def test_workflow_metadata_file_is_readable_on_disk(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    project = projects.create("Circus")
    workflows = WorkflowRepository(tmp_path)
    created = workflows.create(project.id, _workflow(project.id))

    metadata_path = (
        tmp_path / project.slug / "workflows" / str(created.id) / "workflow.json"
    )
    serialized = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert serialized["id"] == str(created.id)
    assert "api_key" not in json.dumps(serialized).lower()
