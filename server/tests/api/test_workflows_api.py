from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_project_service,
    get_workflow_service,
)
from app.main import app
from app.repositories.project_repository import ProjectRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.services.project_service import ProjectService
from app.services.workflow_service import WorkflowService
from app.services.workflow_validation import WorkflowValidator


@pytest.fixture
def client(tmp_path):
    project_service = ProjectService(ProjectRepository(tmp_path))
    workflow_service = WorkflowService(
        WorkflowRepository(tmp_path),
        WorkflowValidator(),
    )
    app.dependency_overrides[get_project_service] = lambda: project_service
    app.dependency_overrides[get_workflow_service] = lambda: workflow_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _workflow_payload() -> dict:
    return {
        "name": "Generation",
        "nodes": [
            {"id": "input", "type": "character_input"},
            {"id": "prompt", "type": "prompt_variant"},
            {
                "id": "generate",
                "type": "image_generation",
                "connector_id": "mock-generation",
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


def test_workflow_crud_round_trip_through_the_api(client):
    project = client.post("/api/projects", json={"name": "Circus"}).json()
    url = f"/api/projects/{project['id']}/workflows"

    created = client.post(url, json=_workflow_payload())
    assert created.status_code == 201
    workflow = created.json()

    assert workflow["project_id"] == project["id"]
    assert workflow["name"] == "Generation"
    assert len(workflow["nodes"]) == 4
    assert len(workflow["edges"]) == 3

    listed = client.get(url)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [workflow["id"]]

    fetched = client.get(f"{url}/{workflow['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == workflow

    updated_payload = _workflow_payload()
    updated_payload["name"] = "Generation v2"
    updated = client.put(f"{url}/{workflow['id']}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Generation v2"

    full_payload = {
        "schema_version": 1,
        "id": workflow["id"],
        "project_id": project["id"],
        "name": "Generation v3",
        "nodes": workflow["nodes"],
        "edges": workflow["edges"],
    }
    full_update = client.put(f"{url}/{workflow['id']}", json=full_payload)
    assert full_update.status_code == 200
    assert full_update.json()["name"] == "Generation v3"

    deleted = client.delete(f"{url}/{workflow['id']}")
    assert deleted.status_code == 204
    assert client.get(url).json() == []


def test_workflow_api_rejects_invalid_workflows(client):
    project = client.post("/api/projects", json={"name": "Circus"}).json()
    url = f"/api/projects/{project['id']}/workflows"

    cyclic = _workflow_payload()
    cyclic["edges"].append(
        {
            "id": "e4",
            "source_node_id": "results",
            "source_port": "image",
            "target_node_id": "generate",
            "target_port": "image",
        }
    )
    assert client.post(url, json=cyclic).status_code == 422

    incompatible = _workflow_payload()
    incompatible["edges"] = [
        {
            "id": "e1",
            "source_node_id": "input",
            "source_port": "character",
            "target_node_id": "generate",
            "target_port": "prompt",
        }
    ]
    assert client.post(url, json=incompatible).status_code == 422

    secret = _workflow_payload()
    secret["nodes"][2]["parameters"] = {"api_key": "sentinel-secret"}
    assert client.post(url, json=secret).status_code == 422

    missing_connector = _workflow_payload()
    del missing_connector["nodes"][2]["connector_id"]
    assert client.post(url, json=missing_connector).status_code == 422


def test_workflow_api_maps_missing_workflow_to_404(client):
    project = client.post("/api/projects", json={"name": "Circus"}).json()
    url = f"/api/projects/{project['id']}/workflows"

    assert client.get(f"{url}/{uuid4()}").status_code == 404
    assert client.delete(f"{url}/{uuid4()}").status_code == 404


def test_workflow_node_definitions_endpoint(client):
    response = client.get("/api/workflow-node-definitions")

    assert response.status_code == 200
    definitions = response.json()
    assert len(definitions) == 9
    assert {definition["type"] for definition in definitions} == {
        "character_input",
        "prompt_variant",
        "prompt_concatenator",
        "text_iterator",
        "image_generation",
        "result_set",
        "selection",
        "upscale",
        "export",
    }
    assert "api_key" not in repr(definitions).lower()
