import hashlib
import io
import shutil
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.dependencies import (
    get_asset_service,
    get_character_service,
    get_project_service,
)
from app.main import app
from app.repositories.asset_repository import AssetRepository
from app.repositories.character_repository import CharacterRepository
from app.repositories.project_repository import ProjectRepository
from app.services.asset_service import AssetService
from app.services.character_service import CharacterService
from app.services.project_service import ProjectService
from app.services.thumbnail_service import ThumbnailService


def image_bytes(format_name: str, size: tuple[int, int] = (80, 60)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, (97, 92, 80)).save(output, format=format_name)
    return output.getvalue()


def build_asset_service(root: Path, max_bytes: int = 1024 * 1024) -> AssetService:
    return AssetService(
        AssetRepository(root),
        ThumbnailService(
            max_width=2048,
            max_height=2048,
            max_pixels=4_000_000,
            thumbnail_max_dimension=64,
        ),
        max_reference_bytes=max_bytes,
    )


@pytest.fixture
def asset_client(tmp_path):
    project_service = ProjectService(ProjectRepository(tmp_path))
    character_service = CharacterService(CharacterRepository(tmp_path))
    asset_service = build_asset_service(tmp_path)
    app.dependency_overrides[get_project_service] = lambda: project_service
    app.dependency_overrides[get_character_service] = lambda: character_service
    app.dependency_overrides[get_asset_service] = lambda: asset_service
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "Circus"}).json()
        character = client.post(
            f"/api/projects/{project['id']}/characters",
            json={"name": "Auguste"},
        ).json()
        yield client, tmp_path, project, character, asset_service
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("format_name", "filename", "media_type", "extension"),
    [
        ("PNG", "reference.png", "image/png", ".png"),
        ("JPEG", "reference.jpeg", "image/jpeg", ".jpg"),
        ("WEBP", "reference.webp", "image/webp", ".webp"),
    ],
)
def test_imports_supported_images_and_serves_content_and_thumbnail(
    asset_client,
    format_name,
    filename,
    media_type,
    extension,
):
    client, root, project, character, _service = asset_client
    content = image_bytes(format_name)
    url = (
        f"/api/projects/{project['id']}/characters/"
        f"{character['id']}/references"
    )

    response = client.post(
        url,
        data={"expected_revision": character["revision"]},
        files={"file": (filename, content, media_type)},
    )

    assert response.status_code == 201
    updated = response.json()
    asset = updated["assets"][0]
    assert updated["revision"] == character["revision"] + 1
    assert asset["kind"] == "reference"
    assert asset["media_type"] == media_type
    assert asset["sha256"] == hashlib.sha256(content).hexdigest()
    assert asset["relative_path"].endswith(extension)
    assert "\\" not in asset["relative_path"]
    assert str(root) not in str(asset)

    content_response = client.get(f"/api/assets/{asset['id']}/content")
    thumbnail_response = client.get(f"/api/assets/{asset['id']}/thumbnail")
    assert content_response.status_code == 200
    assert content_response.content == content
    assert content_response.headers["content-type"] == media_type
    assert content_response.headers["x-content-type-options"] == "nosniff"
    assert thumbnail_response.status_code == 200
    assert thumbnail_response.headers["content-type"] == "image/png"
    with Image.open(io.BytesIO(thumbnail_response.content)) as thumbnail:
        assert thumbnail.format == "PNG"
        assert max(thumbnail.size) <= 64


def test_identical_uploads_remain_distinct_and_delete_is_explicit(asset_client):
    client, _root, project, character, service = asset_client
    content = image_bytes("PNG")
    url = (
        f"/api/projects/{project['id']}/characters/"
        f"{character['id']}/references"
    )
    first = client.post(
        url,
        data={"expected_revision": 0},
        files={"file": ("same.png", content, "image/png")},
    ).json()
    second = client.post(
        url,
        data={"expected_revision": first["revision"]},
        files={"file": ("same.png", content, "image/png")},
    ).json()
    first_asset, second_asset = second["assets"]

    assert first_asset["id"] != second_asset["id"]
    assert first_asset["sha256"] == second_asset["sha256"]
    first_location = service.assets.locate(first_asset["id"])
    deleted = client.delete(
        f"{url}/{first_asset['id']}",
        params={"expected_revision": second["revision"]},
    )
    assert deleted.status_code == 200
    assert [asset["id"] for asset in deleted.json()["assets"]] == [
        second_asset["id"]
    ]
    assert not first_location.content_path.exists()
    assert not first_location.thumbnail_path.exists()
    assert client.get(f"/api/assets/{first_asset['id']}/content").status_code == 404


@pytest.mark.parametrize(
    ("filename", "media_type", "content", "expected_status"),
    [
        ("../escape.png", "image/png", image_bytes("PNG"), 422),
        ("fake.png", "image/png", b"not an image", 415),
        ("fake.png", "image/jpeg", image_bytes("PNG"), 415),
        ("fake.jpg", "image/jpeg", image_bytes("PNG"), 415),
        ("fake.gif", "image/gif", b"GIF89a", 415),
    ],
)
def test_rejects_unsafe_or_deceptive_uploads(
    asset_client, filename, media_type, content, expected_status
):
    client, _root, project, character, _service = asset_client
    url = (
        f"/api/projects/{project['id']}/characters/"
        f"{character['id']}/references"
    )

    response = client.post(
        url,
        data={"expected_revision": character["revision"]},
        files={"file": (filename, content, media_type)},
    )

    assert response.status_code == expected_status
    reloaded = client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}"
    ).json()
    assert reloaded["assets"] == []


def test_rejects_oversized_and_stale_uploads_without_publishing_files(
    asset_client,
):
    client, root, project, character, _service = asset_client
    limited_service = build_asset_service(root, max_bytes=32)
    app.dependency_overrides[get_asset_service] = lambda: limited_service
    url = (
        f"/api/projects/{project['id']}/characters/"
        f"{character['id']}/references"
    )
    oversized = client.post(
        url,
        data={"expected_revision": 0},
        files={"file": ("large.png", image_bytes("PNG"), "image/png")},
    )
    assert oversized.status_code == 413

    app.dependency_overrides[get_asset_service] = lambda: build_asset_service(root)
    first = client.post(
        url,
        data={"expected_revision": 0},
        files={"file": ("first.png", image_bytes("PNG"), "image/png")},
    )
    stale = client.post(
        url,
        data={"expected_revision": 0},
        files={"file": ("stale.png", image_bytes("PNG"), "image/png")},
    )
    assert first.status_code == 201
    assert stale.status_code == 409
    assert len(list(root.glob("**/references/*"))) == 1
    assert len(list(root.glob("**/thumbnails/*"))) == 1


def test_missing_file_is_reported_without_removing_metadata(asset_client):
    client, _root, project, character, service = asset_client
    url = (
        f"/api/projects/{project['id']}/characters/"
        f"{character['id']}/references"
    )
    updated = client.post(
        url,
        data={"expected_revision": 0},
        files={"file": ("reference.png", image_bytes("PNG"), "image/png")},
    ).json()
    asset = updated["assets"][0]
    service.assets.locate(asset["id"]).content_path.unlink()

    missing = client.get(f"/api/assets/{asset['id']}/thumbnail")
    reloaded = client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}"
    ).json()
    assert missing.status_code == 410
    assert missing.json()["code"] == "asset_file_missing"
    assert reloaded["assets"] == updated["assets"]
    assert reloaded["revision"] == updated["revision"]


def test_assets_remain_readable_after_projects_root_move(asset_client, tmp_path):
    client, root, project, character, _service = asset_client
    url = (
        f"/api/projects/{project['id']}/characters/"
        f"{character['id']}/references"
    )
    content = image_bytes("JPEG")
    updated = client.post(
        url,
        data={"expected_revision": 0},
        files={"file": ("reference.jpg", content, "image/jpeg")},
    ).json()
    asset_id = updated["assets"][0]["id"]
    moved_root = tmp_path.parent / f"{tmp_path.name}-moved"
    shutil.copytree(root, moved_root)

    moved_service = build_asset_service(moved_root)

    assert moved_service.get_content(asset_id).path.read_bytes() == content


def test_metadata_failure_rolls_back_published_files(
    asset_client, monkeypatch
):
    client, root, project, character, service = asset_client

    def fail_write(_directory, _character):
        raise OSError("disk failure")

    monkeypatch.setattr(service.assets.characters, "_write", fail_write)

    with pytest.raises(OSError, match="disk failure"):
        service.import_reference(
            UUID(project["id"]),
            UUID(character["id"]),
            expected_revision=0,
            filename="reference.png",
            declared_media_type="image/png",
            source=io.BytesIO(image_bytes("PNG")),
        )

    assert list(root.glob("**/references/*")) == []
    assert list(root.glob("**/thumbnails/*")) == []
    reloaded = client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}"
    ).json()
    assert reloaded["assets"] == []


def test_delete_metadata_failure_leaves_files_and_asset_untouched(
    asset_client, monkeypatch
):
    client, _root, project, character, service = asset_client
    url = (
        f"/api/projects/{project['id']}/characters/"
        f"{character['id']}/references"
    )
    updated = client.post(
        url,
        data={"expected_revision": 0},
        files={"file": ("reference.png", image_bytes("PNG"), "image/png")},
    ).json()
    asset = updated["assets"][0]
    location = service.assets.locate(asset["id"])

    def fail_write(_directory, _character):
        raise OSError("disk failure")

    monkeypatch.setattr(service.assets.characters, "_write", fail_write)

    with pytest.raises(OSError, match="disk failure"):
        service.delete_reference(
            UUID(project["id"]),
            UUID(character["id"]),
            UUID(asset["id"]),
            expected_revision=updated["revision"],
        )

    assert location.content_path.is_file()
    assert location.thumbnail_path.is_file()
    persisted = CharacterRepository(_root).get(project["id"], character["id"])
    assert [item.id for item in persisted.assets] == [UUID(asset["id"])]
