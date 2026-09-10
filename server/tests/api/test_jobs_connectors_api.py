import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_character_service,
    get_connector_service,
    get_job_service,
    get_project_service,
    get_run_service,
    get_workflow_service,
)
from app.main import app
from app.repositories.asset_repository import AssetRepository
from app.repositories.character_repository import CharacterRepository
from app.repositories.job_repository import JobRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.run_repository import RunRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.services.character_service import CharacterService
from app.services.connector_service import ConnectorService
from app.services.job_runner import JobRunner
from app.services.project_service import ProjectService
from app.services.run_service import RunService
from app.services.workflow_executor import WorkflowExecutor
from app.services.workflow_service import WorkflowService
from app.services.workflow_validation import WorkflowValidator


@pytest.fixture
def client(tmp_path):
    project_service = ProjectService(ProjectRepository(tmp_path))
    character_service = CharacterService(CharacterRepository(tmp_path))
    workflow_service = WorkflowService(
        WorkflowRepository(tmp_path), WorkflowValidator()
    )
    assets = AssetRepository(tmp_path)
    jobs = JobRunner(JobRepository(tmp_path))
    run_service = RunService(
        runs=RunRepository(tmp_path),
        jobs=jobs,
        executor=WorkflowExecutor(jobs, assets, WorkflowRepository(tmp_path)),
    )
    overrides = {
        get_project_service: lambda: project_service,
        get_character_service: lambda: character_service,
        get_workflow_service: lambda: workflow_service,
        get_run_service: lambda: run_service,
        get_job_service: lambda: jobs,
        get_connector_service: lambda: ConnectorService(),
    }
    for dependency, provider in overrides.items():
        app.dependency_overrides[dependency] = provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _generation_payload() -> dict:
    return {
        "name": "Generation",
        "nodes": [
            {"id": "input", "type": "character_input"},
            {"id": "prompt", "type": "prompt_variant"},
            {
                "id": "generate",
                "type": "image_generation",
                "connector_id": "mock-generation",
                "parameters": {"width": 64, "height": 64},
            },
            {"id": "results", "type": "result_set"},
        ],
        "edges": [
            {
                "id": "e1",
                "source_node_id": "input",
                "source_port": "character",
                "target_node_id": "prompt",
                "target_port": "character",
            },
            {
                "id": "e2",
                "source_node_id": "prompt",
                "source_port": "prompt",
                "target_node_id": "generate",
                "target_port": "prompt",
            },
            {
                "id": "e3",
                "source_node_id": "generate",
                "source_port": "image",
                "target_node_id": "results",
                "target_port": "image",
            },
        ],
    }


def test_connectors_endpoints_are_available(client):
    response = client.get("/api/connectors")
    assert response.status_code == 200
    connectors = response.json()
    assert {item["id"] for item in connectors} == {
        "muapi-generation",
        "muapi-upscale",
        "mock-generation",
        "mock-upscale",
    }

    check = client.post("/api/connectors/mock-generation/check")
    assert check.status_code == 200
    assert check.json()["available"] is True


def test_run_workflow_end_to_end_via_api(client):
    project = client.post("/api/projects", json={"name": "Circus"}).json()
    character = client.post(
        f"/api/projects/{project['id']}/characters",
        json={"name": "Auguste"},
    ).json()
    workflow = client.post(
        f"/api/projects/{project['id']}/workflows",
        json=_generation_payload(),
    ).json()

    run = client.post(
        f"/api/projects/{project['id']}/workflow-runs",
        json={"workflow_id": workflow["id"], "character_id": character["id"]},
    )
    assert run.status_code == 201
    run_body = run.json()
    assert run_body["status"] == "completed"
    assert run_body["job_ids"]

    fetched = client.get(f"/api/workflow-runs/{run_body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "completed"

    job = client.get(f"/api/jobs/{run_body['job_ids'][0]}")
    assert job.status_code == 200
    assert job.json()["status"] == "completed"


def test_job_cancel_and_retry_through_api(client):
    project = client.post("/api/projects", json={"name": "Circus"}).json()
    character = client.post(
        f"/api/projects/{project['id']}/characters",
        json={"name": "Auguste"},
    ).json()
    workflow = client.post(
        f"/api/projects/{project['id']}/workflows",
        json=_generation_payload(),
    ).json()
    run = client.post(
        f"/api/projects/{project['id']}/workflow-runs",
        json={"workflow_id": workflow["id"], "character_id": character["id"]},
    ).json()
    job_id = run["job_ids"][0]

    cancelled = client.post(f"/api/jobs/{job_id}/cancel")
    assert cancelled.status_code == 422
    assert "termine" in cancelled.json()["detail"]
