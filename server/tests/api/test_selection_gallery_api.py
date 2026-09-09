import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.dependencies import (
    get_asset_service,
    get_character_service,
    get_export_service,
    get_gallery_service,
    get_project_service,
    get_selection_service,
)
from app.main import app
from app.repositories.asset_repository import AssetRepository
from app.repositories.character_repository import CharacterRepository
from app.repositories.project_repository import ProjectRepository
from app.services.asset_service import AssetService
from app.services.character_service import CharacterService
from app.services.export_service import ExportService
from app.services.gallery_service import GalleryService
from app.services.project_service import ProjectService
from app.services.selection_service import SelectionService
from app.services.thumbnail_service import ThumbnailService


def image_bytes(color=(97, 92, 80)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (80, 60), color).save(output, format="PNG")
    return output.getvalue()


def build_thumbnail_service() -> ThumbnailService:
    return ThumbnailService(
        max_width=2048,
        max_height=2048,
        max_pixels=4_000_000,
        thumbnail_max_dimension=64,
    )


@pytest.fixture
def client(tmp_path):
    thumbnails = build_thumbnail_service()
    project_service = ProjectService(ProjectRepository(tmp_path))
    character_service = CharacterService(CharacterRepository(tmp_path))
    asset_repository = AssetRepository(tmp_path)
    asset_service = AssetService(
        asset_repository,
        thumbnails,
        max_reference_bytes=1024 * 1024,
    )
    selection_service = SelectionService(asset_repository)
    export_service = ExportService(asset_repository, thumbnails)
    gallery_service = GalleryService(CharacterRepository(tmp_path), asset_repository)
    overrides = {
        get_project_service: lambda: project_service,
        get_character_service: lambda: character_service,
        get_asset_service: lambda: asset_service,
        get_selection_service: lambda: selection_service,
        get_export_service: lambda: export_service,
        get_gallery_service: lambda: gallery_service,
    }
    for dependency, provider in overrides.items():
        app.dependency_overrides[dependency] = provider
    with TestClient(app) as test_client:
        project = test_client.post("/api/projects", json={"name": "Circus"}).json()
        character = test_client.post(
            f"/api/projects/{project['id']}/characters",
            json={"name": "Auguste"},
        ).json()
        yield test_client, tmp_path, project, character, asset_repository
    app.dependency_overrides.clear()


def import_reference(client, project, character, revision, color=(97, 92, 80)):
    return client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}/references",
        data={"expected_revision": revision},
        files={"file": ("reference.png", image_bytes(color), "image/png")},
    ).json()


def test_favorite_rejected_and_selection_are_independent(client):
    test_client, _root, project, character, _assets = client
    first = import_reference(test_client, project, character, 0)
    second = import_reference(
        test_client, project, first, first["revision"], (10, 20, 30)
    )
    first_asset, second_asset = second["assets"]

    favorited = test_client.patch(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/assets/{first_asset['id']}",
        json={
            "expected_revision": second["revision"],
            "classification": "favorite",
        },
    )
    assert favorited.status_code == 200

    selected = test_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}/selection",
        json={
            "expected_revision": favorited.json()["revision"],
            "asset_id": second_asset["id"],
        },
    )
    assert selected.status_code == 200
    body = selected.json()
    assert body["selected_asset_id"] == second_asset["id"]
    assert body["assets"][0]["classification"] == "favorite"
    assert body["assets"][1]["classification"] == "neutral"

    gallery = test_client.get(f"/api/projects/{project['id']}/gallery")
    assert gallery.status_code == 200
    item = gallery.json()[0]
    assert item["character_id"] == character["id"]
    assert item["selected_asset"]["id"] == second_asset["id"]
    assert item["selected_asset"]["thumbnail_relative_path"] is not None


def test_gallery_returns_placeholder_item_without_selection(client):
    test_client, _root, project, character, _assets = client

    gallery = test_client.get(f"/api/projects/{project['id']}/gallery")

    assert gallery.status_code == 200
    assert gallery.json() == [
        {
            "character_id": character["id"],
            "character_name": "Auguste",
            "character_slug": "auguste",
            "selected_asset": None,
        }
    ]


def test_export_selected_is_deterministic_and_does_not_overwrite(client):
    test_client, root, project, character, assets = client
    updated = import_reference(test_client, project, character, 0)
    asset = updated["assets"][0]
    selected = test_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}/selection",
        json={
            "expected_revision": updated["revision"],
            "asset_id": asset["id"],
        },
    ).json()
    source_path = assets.locate(asset["id"]).content_path

    exported = test_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}/exports",
        json={"expected_revision": selected["revision"]},
    )
    assert exported.status_code == 201
    export_asset = exported.json()["assets"][-1]
    assert export_asset["kind"] == "export"
    assert assets.locate(export_asset["id"]).content_path.is_file()
    assert source_path.is_file()

    duplicate = test_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}/exports",
        json={"expected_revision": exported.json()["revision"]},
    )
    assert duplicate.status_code == 409
    assert len(list(root.glob("**/exports/*"))) == 1


def test_missing_selected_asset_file_keeps_metadata_visible(client):
    test_client, _root, project, character, assets = client
    updated = import_reference(test_client, project, character, 0)
    asset = updated["assets"][0]
    selected = test_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}/selection",
        json={
            "expected_revision": updated["revision"],
            "asset_id": asset["id"],
        },
    ).json()
    assets.locate(asset["id"]).content_path.unlink()

    patched = test_client.patch(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/assets/{asset['id']}",
        json={
            "expected_revision": selected["revision"],
            "classification": "rejected",
        },
    )
    assert patched.status_code == 200
    assert patched.json()["assets"][0]["classification"] == "rejected"

    gallery = test_client.get(f"/api/projects/{project['id']}/gallery")
    assert gallery.status_code == 200
    assert gallery.json()[0]["selected_asset"]["id"] == asset["id"]
    assert test_client.get(f"/api/assets/{asset['id']}/thumbnail").status_code == 410
