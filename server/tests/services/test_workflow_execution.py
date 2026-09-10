
from PIL import Image

from app.connectors.mock_generation import MockGenerationConnector
from app.domain.models import (
    Asset,
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
from app.services.character_service import CharacterService
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


def _generation_workflow_with_empty_prompt(project_id):
    workflow = _generation_workflow(project_id)
    nodes = [
        node.model_copy(update={"parameters": {"prompt_text": ""}})
        if node.type == "prompt_variant"
        else node
        for node in workflow.nodes
    ]
    return workflow.model_copy(update={"nodes": nodes})


def _concatenator_workflow(project_id):
    return Workflow(
        project_id=project_id,
        name="Concatenation",
        nodes=[
            WorkflowNode(
                id="prompt-a",
                type="prompt_variant",
                parameters={"prompt_text": "Premier prompt."},
            ),
            WorkflowNode(
                id="prompt-b",
                type="prompt_variant",
                parameters={"prompt_text": "Second prompt."},
            ),
            WorkflowNode(
                id="concat",
                type="prompt_concatenator",
                parameters={
                    "additional_text": "Texte additionnel.",
                    "input_count": 2,
                },
            ),
            WorkflowNode(
                id="generate",
                type="image_generation",
                connector_id="mock-generation",
                parameters={"width": 64, "height": 64},
            ),
        ],
        edges=[
            WorkflowEdge(
                id="e1",
                source_node_id="prompt-a",
                source_port="prompt",
                target_node_id="concat",
                target_port="prompt_1",
            ),
            WorkflowEdge(
                id="e2",
                source_node_id="prompt-b",
                source_port="prompt",
                target_node_id="concat",
                target_port="prompt_2",
            ),
            WorkflowEdge(
                id="e3",
                source_node_id="concat",
                source_port="prompt",
                target_node_id="generate",
                target_port="prompt",
            ),
        ],
    )


def _text_iterator_workflow(project_id):
    return Workflow(
        project_id=project_id,
        name="Iteration texte",
        nodes=[
            WorkflowNode(
                id="iterator",
                type="text_iterator",
                parameters={"items": ["", "Prompt itere."]},
            ),
            WorkflowNode(
                id="generate",
                type="image_generation",
                connector_id="mock-generation",
                parameters={"width": 64, "height": 64},
            ),
        ],
        edges=[
            WorkflowEdge(
                id="e1",
                source_node_id="iterator",
                source_port="text",
                target_node_id="generate",
                target_port="prompt",
            ),
        ],
    )


def _terminal_generation_workflow(project_id):
    return Workflow(
        project_id=project_id,
        name="Generation terminale",
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
    project, character, assets, jobs, workflows, runs, executor = _setup(tmp_path)
    workflow = workflows.create(project.id, _generation_workflow(project.id))

    run = _run(project, workflow, runs, executor, character.id)

    assert run.status == RunStatus.COMPLETED
    assert run.job_ids
    reloaded = assets.get_character(project.id, character.id)
    assert len(reloaded.assets) == 1
    assert reloaded.assets[0].kind == AssetKind.GENERATION
    assert reloaded.assets[0].relative_path.startswith("Circus/generations/")
    assert reloaded.assets[0].thumbnail_relative_path.startswith(
        "Circus/thumbnails/"
    )
    job = jobs.get_job(project.id, run.job_ids[0])
    assert job.output_asset_ids == [reloaded.assets[0].id]
    content = tmp_path / project.slug / reloaded.assets[0].relative_path
    assert content.is_file()
    with Image.open(content) as image:
        assert image.size == (64, 64)


def test_empty_prompt_node_uses_active_character_prompt(tmp_path):
    project, character, _, jobs, workflows, runs, executor = _setup(tmp_path)
    characters = CharacterService(CharacterRepository(tmp_path))
    character = characters.create_prompt(
        project.id,
        character.id,
        expected_revision=character.revision,
        text="Portrait actif issu de la fiche personnage.",
        block_ids=[],
    )
    active_prompt = character.prompt_versions[0]
    character = characters.activate_prompt(
        project.id,
        character.id,
        active_prompt.id,
        expected_revision=character.revision,
    )
    workflow = workflows.create(
        project.id,
        _generation_workflow_with_empty_prompt(project.id),
    )

    run = _run(project, workflow, runs, executor, character.id)

    assert run.status == RunStatus.COMPLETED
    job = jobs.get_job(project.id, run.job_ids[0])
    assert job.inputs["prompt"] == "Portrait actif issu de la fiche personnage."


def test_prompt_concatenator_combines_inputs_and_local_text(tmp_path):
    project, character, _, jobs, workflows, runs, executor = _setup(tmp_path)
    workflow = workflows.create(project.id, _concatenator_workflow(project.id))

    run = _run(project, workflow, runs, executor, character.id)

    assert run.status == RunStatus.COMPLETED
    job = jobs.get_job(project.id, run.job_ids[0])
    assert job.inputs["prompt"] == (
        "Premier prompt.\n\nSecond prompt.\n\nTexte additionnel."
    )


def test_text_iterator_outputs_first_non_empty_item(tmp_path):
    project, character, _, jobs, workflows, runs, executor = _setup(tmp_path)
    workflow = workflows.create(project.id, _text_iterator_workflow(project.id))

    run = _run(project, workflow, runs, executor, character.id)

    assert run.status == RunStatus.COMPLETED
    job = jobs.get_job(project.id, run.job_ids[0])
    assert job.inputs["prompt"] == "Prompt itere."


def test_terminal_generation_publishes_asset(tmp_path):
    project, character, assets, jobs, workflows, runs, executor = _setup(tmp_path)
    workflow = workflows.create(project.id, _terminal_generation_workflow(project.id))

    run = _run(project, workflow, runs, executor, character.id)

    assert run.status == RunStatus.COMPLETED
    reloaded = assets.get_character(project.id, character.id)
    assert len(reloaded.assets) == 1
    assert reloaded.assets[0].kind == AssetKind.GENERATION
    job = jobs.get_job(project.id, run.job_ids[0])
    assert job.output_asset_ids == [reloaded.assets[0].id]


def test_migrate_publishable_assets_to_project_media_folder(tmp_path):
    project, character, assets, _, _, _, _ = _setup(tmp_path)
    asset = Asset(
        kind=AssetKind.GENERATION,
        relative_path=f"characters/{character.slug}/generations/legacy.png",
        thumbnail_relative_path="thumbnails/legacy.png",
        media_type="image/png",
        width=16,
        height=16,
    )
    project_directory = tmp_path / project.slug
    old_content = project_directory / asset.relative_path
    old_thumbnail = project_directory / asset.thumbnail_relative_path
    old_content.parent.mkdir(parents=True, exist_ok=True)
    old_thumbnail.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), (97, 92, 80)).save(old_content)
    Image.new("RGB", (8, 8), (97, 92, 80)).save(old_thumbnail)
    CharacterRepository(tmp_path).save(
        character.model_copy(update={"assets": [asset]})
    )

    migrated = assets.migrate_publishable_assets(project.id)

    assert len(migrated) == 1
    reloaded = assets.get_character(project.id, character.id)
    moved = reloaded.assets[0]
    assert moved.relative_path == f"Circus/generations/{asset.id}.png"
    assert moved.thumbnail_relative_path == f"Circus/thumbnails/{asset.id}.png"
    assert (project_directory / moved.relative_path).is_file()
    assert (project_directory / moved.thumbnail_relative_path).is_file()
    assert not old_content.exists()
    assert not old_thumbnail.exists()


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
