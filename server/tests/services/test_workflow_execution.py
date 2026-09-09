
from PIL import Image

from app.connectors.mock_generation import MockGenerationConnector
from app.domain.models import (
    AssetKind,
    RunStatus,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowRun,
)
from app.repositories.asset_repository import AssetRepository
from app.repositories.character_repository import CharacterRepository
from app.repositories.job_repository import JobRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.run_repository import RunRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.services.job_runner import JobRunner
from app.services.workflow_executor import WorkflowExecutor


def _setup(tmp_path):
    projects = ProjectRepository(tmp_path)
    project = projects.create("Circus")
    character = CharacterRepository(tmp_path).create(project.id, "Auguste")
    assets = AssetRepository(tmp_path)
    jobs = JobRunner(JobRepository(tmp_path))
    workflows = WorkflowRepository(tmp_path)
    runs = RunRepository(tmp_path)
    executor = WorkflowExecutor(jobs, assets, workflows)
    return project, character, assets, jobs, workflows, runs, executor


def _generation_workflow(project_id):
    return Workflow(
        project_id=project_id,
        name="Generation",
        nodes=[
            WorkflowNode(id="input", type="character_input"),
            WorkflowNode(
                id="prompt",
                type="prompt_variant",
                parameters={"prompt_text": "un clown melancolique"},
            ),
            WorkflowNode(
                id="generate",
                type="image_generation",
                connector_id="mock-generation",
                parameters={"width": 64, "height": 64},
            ),
            WorkflowNode(id="results", type="result_set"),
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


def _upscale_workflow(project_id):
    return Workflow(
        project_id=project_id,
        name="Upscale",
        nodes=[
            WorkflowNode(id="select", type="selection"),
            WorkflowNode(
                id="upscale",
                type="upscale",
                connector_id="mock-upscale",
                parameters={"scale": 2},
            ),
            WorkflowNode(id="export", type="export"),
        ],
        edges=[
            WorkflowEdge(
                id="e1",
                source_node_id="select",
                source_port="image",
                target_node_id="upscale",
                target_port="image",
            ),
            WorkflowEdge(
                id="e2",
                source_node_id="upscale",
                source_port="image",
                target_node_id="export",
                target_port="image",
            ),
        ],
    )


def _run(project, workflow, runs, executor, character_id):
    run = WorkflowRun(
        project_id=project.id,
        workflow_id=workflow.id,
        character_id=character_id,
    )
    run = runs.create(project.id, run)
    return executor.execute(project.id, workflow.id, run)


def test_generation_workflow_runs_and_persists_asset(tmp_path):
    project, character, assets, _, workflows, runs, executor = _setup(tmp_path)
    workflow = workflows.create(project.id, _generation_workflow(project.id))

    run = _run(project, workflow, runs, executor, character.id)

    assert run.status == RunStatus.COMPLETED
    assert run.job_ids
    reloaded = assets.get_character(project.id, character.id)
    assert len(reloaded.assets) == 1
    assert reloaded.assets[0].kind == AssetKind.GENERATION
    content = tmp_path / project.slug / reloaded.assets[0].relative_path
    assert content.is_file()
    with Image.open(content) as image:
        assert image.size == (64, 64)


def test_upscale_workflow_runs_generation_then_upscale(tmp_path):
    project, character, assets, _, workflows, runs, executor = _setup(tmp_path)
    generation = workflows.create(project.id, _generation_workflow(project.id))
    _run(project, generation, runs, executor, character.id)

    reloaded = assets.get_character(project.id, character.id)
    generation_asset = reloaded.assets[0]
    character_dir = (
        tmp_path / project.slug / "characters" / character.slug / "character.json"
    )

    from app.storage.atomic_json import read_json, write_json_atomic

    data = read_json(character_dir)
    data["selected_asset_id"] = str(generation_asset.id)
    write_json_atomic(character_dir, data)
    selected = assets.get_character(project.id, character.id)
    assert selected.selected_asset_id == generation_asset.id

    upscale = workflows.create(project.id, _upscale_workflow(project.id))
    run = _run(project, upscale, runs, executor, character.id)

    assert run.status == RunStatus.COMPLETED
    final = assets.get_character(project.id, character.id)
    kinds = {asset.kind for asset in final.assets}
    assert AssetKind.UPSCALE in kinds
    assert AssetKind.EXPORT in kinds


def test_connector_failure_leaves_assets_unchanged(tmp_path, monkeypatch):
    project, character, assets, _, workflows, runs, executor = _setup(tmp_path)
    workflow = workflows.create(project.id, _generation_workflow(project.id))

    def failing(self, parameters, context):
        raise RuntimeError("provider unreachable")

    monkeypatch.setattr(MockGenerationConnector, "submit", failing)

    run = _run(project, workflow, runs, executor, character.id)

    assert run.status == RunStatus.FAILED
    reloaded = assets.get_character(project.id, character.id)
    assert reloaded.assets == []


def test_topological_propagation_uses_upstream_prompt(tmp_path):
    project, character, assets, _, workflows, runs, executor = _setup(tmp_path)
    workflow = workflows.create(project.id, _generation_workflow(project.id))

    run = _run(project, workflow, runs, executor, character.id)
    assert run.status == RunStatus.COMPLETED

    reloaded = assets.get_character(project.id, character.id)
    assert len(reloaded.assets) == 1
    assert reloaded.assets[0].kind == AssetKind.GENERATION
