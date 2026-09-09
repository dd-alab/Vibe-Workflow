import os
import shutil
import tempfile
from pathlib import Path
from uuid import UUID

from app.domain.models import Character, CharacterReference, Project, utc_now
from app.storage.atomic_json import read_json, write_json_atomic
from app.storage.locks import project_lock
from app.storage.paths import (
    ensure_internal_directory,
    resolve_within,
    slugify,
    validate_slug,
)

from .errors import ConflictError, CorruptMetadataError, NotFoundError
from .project_repository import ProjectRepository

CHARACTER_DIRECTORIES = ("references", "generations", "upscales", "exports")


class CharacterRepository:
    def __init__(self, root: Path) -> None:
        self.projects = ProjectRepository(root)

    def create(
        self, project_id: UUID | str, name: str, slug: str | None = None
    ) -> Character:
        project_directory = self.projects.path_for(project_id)
        character_slug = validate_slug(slug) if slug is not None else slugify(name)
        with project_lock(project_directory):
            project = self.projects._load(project_directory)
            characters_directory = self._characters_directory(project_directory)
            character_directory = resolve_within(characters_directory, character_slug)
            if character_directory.exists():
                return self._recover_or_reject_existing(
                    project_directory,
                    project,
                    character_directory,
                    character_slug,
                )

            character = Character(
                project_id=project.id,
                name=name.strip(),
                slug=character_slug,
            )

            project_staging = ensure_internal_directory(project_directory, ".staging")
            staging_directory = ensure_internal_directory(project_staging, "characters")
            temporary_directory = Path(
                tempfile.mkdtemp(
                    prefix=f".{character_slug}.",
                    suffix=".tmp",
                    dir=staging_directory,
                )
            )
            try:
                for directory_name in CHARACTER_DIRECTORIES:
                    (temporary_directory / directory_name).mkdir()
                self._write(temporary_directory, character)
                os.replace(temporary_directory, character_directory)
            finally:
                if temporary_directory.exists():
                    shutil.rmtree(temporary_directory)

            try:
                project.characters.append(
                    CharacterReference(id=character.id, slug=character.slug)
                )
                project.revision += 1
                project.updated_at = utc_now()
                self.projects._write(project_directory, project)
            except Exception:
                shutil.rmtree(character_directory)
                raise
            return character

    def list_for_project(self, project_id: UUID | str) -> list[Character]:
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            project = self.projects._load(project_directory)
            self._characters_directory(project_directory)
            return [
                self._load_for_reference(
                    project,
                    reference,
                    resolve_within(
                        project_directory,
                        Path("characters") / reference.slug,
                    ),
                )
                for reference in project.characters
            ]

    def get(self, project_id: UUID | str, character_id: UUID | str) -> Character:
        expected_id = UUID(str(character_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            project = self.projects._load(project_directory)
            self._characters_directory(project_directory)
            reference = next(
                (
                    reference
                    for reference in project.characters
                    if reference.id == expected_id
                ),
                None,
            )
            if reference is not None:
                character_directory = resolve_within(
                    project_directory, Path("characters") / reference.slug
                )
                return self._load_for_reference(project, reference, character_directory)
        raise NotFoundError(f"character '{expected_id}' was not found")

    def save(self, character: Character) -> Character:
        project_directory = self.projects.path_for(character.project_id)
        with project_lock(project_directory):
            project = self.projects._load(project_directory)
            self._characters_directory(project_directory)
            reference = next(
                (
                    reference
                    for reference in project.characters
                    if reference.id == character.id
                ),
                None,
            )
            if reference is None or reference.slug != character.slug:
                raise ConflictError("character identity cannot be changed by save")

            character_directory = resolve_within(
                project_directory, Path("characters") / reference.slug
            )
            current = self._load_for_reference(project, reference, character_directory)
            if current.project_id != character.project_id or current.id != character.id:
                raise ConflictError("character identity does not match its metadata")
            if current.revision != character.revision:
                raise ConflictError("character changed on disk; reload before saving")

            updated = character.model_copy(
                update={
                    "revision": character.revision + 1,
                    "updated_at": utc_now(),
                }
            )
            self._write(character_directory, updated)
            return updated

    @staticmethod
    def metadata_path(character_directory: Path) -> Path:
        return character_directory / "character.json"

    def _load(self, character_directory: Path) -> Character:
        metadata_path = self.metadata_path(character_directory)
        if not metadata_path.exists():
            raise NotFoundError(
                f"character metadata is missing from '{character_directory.name}'"
            )
        return Character.model_validate(read_json(metadata_path))

    def _write(self, character_directory: Path, character: Character) -> None:
        validated = Character.model_validate(character.model_dump(mode="json"))
        write_json_atomic(
            self.metadata_path(character_directory), validated.model_dump(mode="json")
        )

    def _load_for_reference(
        self,
        project: Project,
        reference: CharacterReference,
        character_directory: Path,
    ) -> Character:
        character = self._load(character_directory)
        if (
            character.id != reference.id
            or character.project_id != project.id
            or character.slug != reference.slug
            or character_directory.name != reference.slug
        ):
            raise CorruptMetadataError(
                f"character identity does not match project reference '{reference.id}'"
            )
        return character

    def _recover_or_reject_existing(
        self,
        project_directory: Path,
        project: Project,
        character_directory: Path,
        character_slug: str,
    ) -> Character:
        if any(reference.slug == character_slug for reference in project.characters):
            raise ConflictError(f"character slug '{character_slug}' already exists")

        try:
            character = self._load(character_directory)
        except Exception as error:
            raise CorruptMetadataError(
                f"orphan character '{character_slug}' has invalid metadata"
            ) from error

        if character.project_id != project.id or character.slug != character_slug:
            raise CorruptMetadataError(
                f"orphan character '{character_slug}' has inconsistent identity"
            )
        if any(reference.id == character.id for reference in project.characters):
            raise CorruptMetadataError(
                f"character id '{character.id}' is already indexed with another slug"
            )

        project.characters.append(
            CharacterReference(id=character.id, slug=character.slug)
        )
        project.revision += 1
        project.updated_at = utc_now()
        self.projects._write(project_directory, project)
        return character

    @staticmethod
    def _characters_directory(project_directory: Path) -> Path:
        characters_directory = project_directory / "characters"
        is_junction = getattr(characters_directory, "is_junction", lambda: False)
        if characters_directory.is_symlink() or is_junction():
            raise CorruptMetadataError(
                "characters directory cannot be a symlink or junction"
            )
        resolved = resolve_within(project_directory, "characters")
        if not resolved.is_dir():
            raise CorruptMetadataError("characters directory is missing")
        return resolved
