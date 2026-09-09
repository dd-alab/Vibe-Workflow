import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_character_service, get_project_service
from app.main import app
from app.repositories.character_repository import CharacterRepository
from app.repositories.project_repository import ProjectRepository
from app.services.character_service import CharacterService
from app.services.project_service import ProjectService


@pytest.fixture
def client(tmp_path):
    project_service = ProjectService(ProjectRepository(tmp_path))
    character_service = CharacterService(CharacterRepository(tmp_path))
    app.dependency_overrides[get_project_service] = lambda: project_service
    app.dependency_overrides[get_character_service] = lambda: character_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_project_api_validates_names_maps_missing_resources_and_revisions(client):
    assert client.post("/api/projects", json={"name": "   "}).status_code == 422
    assert client.get(f"/api/projects/{uuid4()}").status_code == 404

    created = client.post("/api/projects", json={"name": "Circus Portraits"})
    assert created.status_code == 201
    project = created.json()

    renamed = client.patch(
        f"/api/projects/{project['id']}",
        json={"expected_revision": 0, "name": "Portraits de cirque"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Portraits de cirque"
    assert renamed.json()["slug"] == project["slug"]
    assert renamed.json()["revision"] == 1

    stale = client.patch(
        f"/api/projects/{project['id']}",
        json={"expected_revision": 0, "name": "Ancien nom"},
    )
    assert stale.status_code == 409
    assert "recharger" in stale.json()["detail"].lower()


@pytest.mark.parametrize("name", ["CON", "漢字", "x" * 120])
def test_project_api_rejects_names_that_cannot_become_safe_slugs(client, name):
    response = client.post("/api/projects", json={"name": name})

    assert response.status_code == 422
    assert "dossier projet valide" in response.json()["detail"]


def test_30_characters_can_be_created_and_listed_through_the_api(client):
    project = client.post(
        "/api/projects", json={"name": "Circus Portraits"}
    ).json()

    created = [
        client.post(
            f"/api/projects/{project['id']}/characters",
            json={"name": f"Personnage {index:02d}"},
        )
        for index in range(30)
    ]

    assert all(response.status_code == 201 for response in created)
    characters = client.get(
        f"/api/projects/{project['id']}/characters"
    ).json()
    reloaded_project = client.get(f"/api/projects/{project['id']}").json()
    assert len(characters) == 30
    assert len(reloaded_project["characters"]) == 30

    invalid_character = client.post(
        f"/api/projects/{project['id']}/characters",
        json={"name": "CON"},
    )
    assert invalid_character.status_code == 422


def test_character_texts_prompt_blocks_and_prompt_history_are_preserved(client):
    project = client.post("/api/projects", json={"name": "Circus"}).json()
    character = client.post(
        f"/api/projects/{project['id']}/characters",
        json={"name": "Auguste melancolique"},
    ).json()
    character_url = (
        f"/api/projects/{project['id']}/characters/{character['id']}"
    )

    edited = client.patch(
        character_url,
        json={
            "expected_revision": character["revision"],
            "short_texts": [{"text": "Un clown silencieux sous la pluie."}],
            "prompt_blocks": [
                {"name": "Lumiere", "text": "clair-obscur de chapiteau"}
            ],
        },
    )
    assert edited.status_code == 200
    character = edited.json()
    text_id = character["short_texts"][0]["id"]
    block_id = character["prompt_blocks"][0]["id"]

    first_prompt = client.post(
        f"{character_url}/prompts",
        json={
            "expected_revision": character["revision"],
            "text": "Portrait serre, regard melancolique.",
            "block_ids": [block_id],
        },
    )
    assert first_prompt.status_code == 201
    character = first_prompt.json()
    first_version = character["prompt_versions"][0]

    activated = client.post(
        f"{character_url}/prompts/{first_version['id']}/activate",
        json={"expected_revision": character["revision"]},
    )
    assert activated.status_code == 200
    character = activated.json()
    assert character["active_prompt_version_id"] == first_version["id"]

    second_prompt = client.post(
        f"{character_url}/prompts",
        json={
            "expected_revision": character["revision"],
            "text": "Portrait frontal, expression retenue.",
            "block_ids": [],
        },
    )
    assert second_prompt.status_code == 201
    character = second_prompt.json()
    assert character["prompt_versions"][0] == first_version
    assert len(character["prompt_versions"]) == 2


    second_version = character["prompt_versions"][1]
    switched = client.post(
        f"{character_url}/prompts/{second_version['id']}/activate",
        json={"expected_revision": character["revision"]},
    )
    assert switched.status_code == 200
    character = switched.json()
    assert character["active_prompt_version_id"] == second_version["id"]
    assert character["prompt_versions"][0] == first_version

    edited_text = client.patch(
        character_url,
        json={
            "expected_revision": character["revision"],
            "short_texts": [
                {"id": text_id, "text": "Un clown immobile sous la pluie."}
            ],
        },
    )
    assert edited_text.status_code == 200
    assert edited_text.json()["short_texts"][0]["id"] == text_id
    assert edited_text.json()["prompt_versions"][0] == first_version


def test_prompt_blocks_referenced_by_history_are_immutable(client):
    project = client.post("/api/projects", json={"name": "Circus"}).json()
    character = client.post(
        f"/api/projects/{project['id']}/characters",
        json={"name": "Ecuyere fantome"},
    ).json()
    character_url = (
        f"/api/projects/{project['id']}/characters/{character['id']}"
    )
    character = client.patch(
        character_url,
        json={
            "expected_revision": 0,
            "prompt_blocks": [{"name": "Palette", "text": "bleu nocturne"}],
        },
    ).json()
    block = character["prompt_blocks"][0]
    character = client.post(
        f"{character_url}/prompts",
        json={
            "expected_revision": character["revision"],
            "text": "Portrait spectral.",
            "block_ids": [block["id"]],
        },
    ).json()

    changed_block = client.patch(
        character_url,
        json={
            "expected_revision": character["revision"],
            "prompt_blocks": [
                {"id": block["id"], "name": "Palette", "text": "rouge vif"}
            ],
        },
    )
    removed_block = client.patch(
        character_url,
        json={
            "expected_revision": character["revision"],
            "prompt_blocks": [],
        },
    )
    unknown_block = client.post(
        f"{character_url}/prompts",
        json={
            "expected_revision": character["revision"],
            "text": "Autre portrait.",
            "block_ids": [str(uuid4())],
        },
    )

    assert changed_block.status_code == 409
    assert removed_block.status_code == 409
    assert unknown_block.status_code == 422


def test_corrupt_project_metadata_returns_a_sanitized_json_error(client, tmp_path):
    corrupt_directory = tmp_path / "corrupt"
    corrupt_directory.mkdir()
    (corrupt_directory / "project.json").write_text("{broken", encoding="utf-8")

    response = client.get("/api/projects")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Les donnees locales n'ont pas pu etre lues."
    }
    assert str(tmp_path) not in json.dumps(response.json())
