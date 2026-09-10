import json
import multiprocessing
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.domain.models import Character, Project, PromptVersion
from app.repositories.character_repository import CharacterRepository
from app.repositories.errors import ConflictError, CorruptMetadataError, RepositoryError
from app.repositories.project_repository import ProjectRepository
from app.storage.atomic_json import write_json_atomic


def _create_character_in_process(root: str, project_id: str, index: int) -> None:
    CharacterRepository(Path(root)).create(project_id, f"Process character {index:02d}")


def test_create_project_builds_readable_directory_tree(tmp_path) -> None:
    project = ProjectRepository(tmp_path).create("Circus Portraits")
    project_directory = tmp_path / "circus_portraits"

    assert project.slug == "circus_portraits"
    assert (project_directory / "project.json").is_file()
    assert {
        "characters",
        "jobs",
        "runs",
        "thumbnails",
        "workflows",
    } <= {path.name for path in project_directory.iterdir() if path.is_dir()}

    serialized = json.loads(
        (project_directory / "project.json").read_text(encoding="utf-8")
    )
    assert serialized["id"] == str(project.id)
    assert "api_key" not in json.dumps(serialized).lower()


def test_project_with_30_characters_survives_root_move(tmp_path) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    projects = ProjectRepository(source_root)
    characters = CharacterRepository(source_root)
    project = projects.create("Circus Portraits")

    created = [
        characters.create(project.id, f"Personnage {index:02d}") for index in range(30)
    ]

    shutil.copytree(source_root, target_root)
    moved_project = ProjectRepository(target_root).get(project.id)
    moved_characters = CharacterRepository(target_root).list_for_project(project.id)

    assert len(moved_project.characters) == 30
    assert {character.id for character in moved_characters} == {
        character.id for character in created
    }


def test_concurrent_character_creation_does_not_lose_entries(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    characters = CharacterRepository(tmp_path)
    project = projects.create("Concurrent project")

    with ThreadPoolExecutor(max_workers=8) as executor:
        created = list(
            executor.map(
                lambda index: characters.create(project.id, f"Character {index:02d}"),
                range(20),
            )
        )

    reloaded = projects.get(project.id)

    assert len(reloaded.characters) == 20
    assert len({reference.id for reference in reloaded.characters}) == 20
    assert len({character.slug for character in created}) == 20


def test_processes_do_not_lose_character_entries(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    project = projects.create("Multiprocess project")
    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(
            target=_create_character_in_process,
            args=(str(tmp_path), str(project.id), index),
        )
        for index in range(6)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)

    assert [process.exitcode for process in processes] == [0] * 6
    assert len(projects.get(project.id).characters) == 6


def test_explicit_unsafe_project_slug_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError):
        ProjectRepository(tmp_path).create("Unsafe", slug="../escape")


def test_failed_project_creation_leaves_no_partial_directory(
    tmp_path, monkeypatch
) -> None:
    projects = ProjectRepository(tmp_path)

    def fail_write(_directory, _project) -> None:
        raise OSError("disk failure")

    monkeypatch.setattr(projects, "_write", fail_write)

    with pytest.raises(OSError, match="disk failure"):
        projects.create("Circus")

    assert not (tmp_path / "circus").exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_failed_project_index_update_rolls_back_new_character(
    tmp_path, monkeypatch
) -> None:
    projects = ProjectRepository(tmp_path)
    characters = CharacterRepository(tmp_path)
    project = projects.create("Circus")

    def fail_write(_directory, _project) -> None:
        raise OSError("disk failure")

    monkeypatch.setattr(characters.projects, "_write", fail_write)

    with pytest.raises(OSError, match="disk failure"):
        characters.create(project.id, "Auguste")

    assert not (tmp_path / "circus" / "characters" / "auguste").exists()
    assert ProjectRepository(tmp_path).get(project.id).characters == []


def test_stale_project_snapshot_cannot_erase_new_character(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    characters = CharacterRepository(tmp_path)
    project = projects.create("Circus")
    stale_project = projects.get(project.id)
    characters.create(project.id, "Auguste")

    with pytest.raises(ConflictError, match="changed on disk"):
        projects.save(stale_project)

    assert len(projects.get(project.id).characters) == 1


def test_character_identity_cannot_be_changed_by_save(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    characters = CharacterRepository(tmp_path)
    project = projects.create("Circus")
    character = characters.create(project.id, "Auguste")
    character.slug = "another-character"

    with pytest.raises(ConflictError, match="identity"):
        characters.save(character)


def test_stale_character_snapshot_cannot_overwrite_newer_edit(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    characters = CharacterRepository(tmp_path)
    project = projects.create("Circus")
    character = characters.create(project.id, "Auguste")
    stale_character = characters.get(project.id, character.id)

    character.name = "Auguste souriant"
    characters.save(character)
    stale_character.name = "Auguste triste"

    with pytest.raises(ConflictError, match="changed on disk"):
        characters.save(stale_character)


def test_project_symlink_cannot_escape_projects_root(tmp_path) -> None:
    projects_root = tmp_path / "projects"
    outside_root = tmp_path / "outside"
    outside_project = ProjectRepository(outside_root).create("Outside")
    projects_root.mkdir()

    try:
        (projects_root / "linked-project").symlink_to(
            outside_root / outside_project.slug,
            target_is_directory=True,
        )
    except OSError:
        pytest.skip("directory symlinks require Windows developer mode")

    with pytest.raises(RepositoryError, match="outside the projects root"):
        ProjectRepository(projects_root).get(outside_project.id)


def test_staging_directory_is_not_listed_as_project(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    staging_project = Project(name="Interrupted", slug="interrupted")
    staging_directory = tmp_path / ".staging" / "interrupted"
    staging_directory.mkdir(parents=True)
    write_json_atomic(
        staging_directory / "project.json",
        staging_project.model_dump(mode="json"),
    )

    assert projects.list() == []


def test_character_creation_recovers_matching_orphan(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    characters = CharacterRepository(tmp_path)
    project = projects.create("Circus")
    orphan = Character(project_id=project.id, name="Auguste", slug="auguste")
    orphan_directory = tmp_path / project.slug / "characters" / orphan.slug
    orphan_directory.mkdir()
    for directory_name in ("references", "generations", "upscales", "exports"):
        (orphan_directory / directory_name).mkdir()
    write_json_atomic(
        orphan_directory / "character.json", orphan.model_dump(mode="json")
    )

    recovered = characters.create(project.id, "Auguste")

    assert recovered.id == orphan.id
    assert projects.get(project.id).characters[0].id == orphan.id


def test_character_metadata_identity_must_match_project_reference(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    characters = CharacterRepository(tmp_path)
    project = projects.create("Circus")
    character = characters.create(project.id, "Auguste")
    metadata_path = (
        tmp_path / project.slug / "characters" / character.slug / "character.json"
    )
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    data["id"] = "9d6874b4-0a49-48f3-bc09-3f48fd8441bd"
    write_json_atomic(metadata_path, data)

    with pytest.raises(CorruptMetadataError, match="identity"):
        characters.get(project.id, character.id)


def test_character_repository_rejects_prompt_history_rewrites(tmp_path) -> None:
    projects = ProjectRepository(tmp_path)
    characters = CharacterRepository(tmp_path)
    project = projects.create("Circus")
    character = characters.create(project.id, "Auguste")
    character.prompt_versions.append(PromptVersion(text="Version originale"))
    character = characters.save(character)

    character.prompt_versions[0] = PromptVersion(text="Version remplacee")

    with pytest.raises(ConflictError, match="prompt history"):
        characters.save(character)
