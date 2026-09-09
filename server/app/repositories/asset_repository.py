import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import UUID

from app.domain.models import Asset, AssetClassification, AssetKind, Character, utc_now
from app.storage.locks import project_lock
from app.storage.paths import ensure_internal_directory, resolve_within

from .character_repository import CharacterRepository
from .errors import ConflictError, CorruptMetadataError, NotFoundError
from .project_repository import ProjectRepository


@dataclass(frozen=True)
class AssetLocation:
    project_id: UUID
    character_id: UUID
    project_directory: Path
    character_directory: Path
    asset: Asset
    content_path: Path
    thumbnail_path: Path | None


class AssetRepository:
    def __init__(self, root: Path) -> None:
        self.projects = ProjectRepository(root)
        self.characters = CharacterRepository(root)

    def get_character(
        self, project_id: UUID | str, character_id: UUID | str
    ) -> Character:
        return self.characters.get(project_id, character_id)

    @contextmanager
    def staging_directory(self, project_id: UUID | str) -> Iterator[Path]:
        project_directory = self.projects.path_for(project_id)
        staging_root = ensure_internal_directory(project_directory, ".staging")
        assets_root = ensure_internal_directory(staging_root, "assets")
        temporary_directory = Path(
            tempfile.mkdtemp(prefix="asset.", suffix=".tmp", dir=assets_root)
        )
        try:
            yield temporary_directory
        finally:
            if temporary_directory.exists():
                shutil.rmtree(temporary_directory)

    def add_reference(
        self,
        project_id: UUID | str,
        character_id: UUID | str,
        *,
        expected_revision: int,
        asset: Asset,
        staged_content_path: Path,
        staged_thumbnail_path: Path,
    ) -> Character:
        project_directory = self.projects.path_for(project_id)
        published: list[Path] = []
        with project_lock(project_directory):
            character, character_directory = self._load_character_locked(
                project_directory, project_id, character_id
            )
            self._check_revision(character, expected_revision)
            content_path, thumbnail_path = self._asset_paths(
                project_directory, character, asset
            )
            if thumbnail_path is None:
                raise CorruptMetadataError("reference thumbnail path is required")
            if content_path.exists() or thumbnail_path.exists():
                raise ConflictError("asset destination already exists")

            try:
                os.replace(staged_content_path, content_path)
                published.append(content_path)
                os.replace(staged_thumbnail_path, thumbnail_path)
                published.append(thumbnail_path)
                data = character.model_dump()
                data["assets"] = [*character.assets, asset]
                data["revision"] = character.revision + 1
                data["updated_at"] = utc_now()
                updated = Character.model_validate(data)
                self.characters._write(character_directory, updated)
                return updated
            except Exception:
                for path in reversed(published):
                    path.unlink(missing_ok=True)
                raise

    def locate(self, asset_id: UUID | str) -> AssetLocation:
        expected_id = UUID(str(asset_id))
        matches: list[AssetLocation] = []
        for project in self.projects.list():
            project_directory = self.projects.path_for(project.id)
            for character in self.characters.list_for_project(project.id):
                for asset in character.assets:
                    if asset.id != expected_id:
                        continue
                    character_directory = resolve_within(
                        project_directory,
                        Path("characters") / character.slug,
                    )
                    if asset.kind == AssetKind.REFERENCE:
                        content_path, thumbnail_path = self._asset_paths(
                            project_directory, character, asset
                        )
                    else:
                        content_path, thumbnail_path = self._publication_paths(
                            project_directory, character, asset
                        )
                    matches.append(
                        AssetLocation(
                            project_id=project.id,
                            character_id=character.id,
                            project_directory=project_directory,
                            character_directory=character_directory,
                            asset=asset,
                            content_path=content_path,
                            thumbnail_path=thumbnail_path,
                        )
                    )
        if not matches:
            raise NotFoundError(f"asset '{expected_id}' was not found")
        if len(matches) > 1:
            raise CorruptMetadataError("asset id is not unique")
        return matches[0]

    def delete_reference(
        self,
        project_id: UUID | str,
        character_id: UUID | str,
        asset_id: UUID | str,
        *,
        expected_revision: int,
    ) -> Character:
        expected_id = UUID(str(asset_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            character, character_directory = self._load_character_locked(
                project_directory, project_id, character_id
            )
            self._check_revision(character, expected_revision)
            asset = next(
                (item for item in character.assets if item.id == expected_id),
                None,
            )
            if asset is None or asset.kind != AssetKind.REFERENCE:
                raise NotFoundError(f"reference asset '{expected_id}' was not found")
            content_path, thumbnail_path = self._asset_paths(
                project_directory, character, asset
            )
            data = character.model_dump()
            data["assets"] = [
                item for item in character.assets if item.id != expected_id
            ]
            if character.selected_asset_id == expected_id:
                data["selected_asset_id"] = None
            data["revision"] = character.revision + 1
            data["updated_at"] = utc_now()
            updated = Character.model_validate(data)

            # Metadata is committed first: a crash may leave harmless orphan files,
            # but never metadata that points to files moved out from under it.
            self.characters._write(character_directory, updated)
            for path in (content_path, thumbnail_path):
                if path is None:
                    continue
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            return updated

    def update_classification(
        self,
        project_id: UUID | str,
        character_id: UUID | str,
        asset_id: UUID | str,
        *,
        expected_revision: int,
        classification: AssetClassification,
    ) -> Character:
        expected_id = UUID(str(asset_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            character, character_directory = self._load_character_locked(
                project_directory, project_id, character_id
            )
            self._check_revision(character, expected_revision)
            found = False
            updated_assets = []
            for asset in character.assets:
                if asset.id != expected_id:
                    updated_assets.append(asset)
                    continue
                found = True
                updated_assets.append(
                    asset.model_copy(update={"classification": classification})
                )
            if not found:
                raise NotFoundError(f"asset '{expected_id}' was not found")
            data = character.model_dump()
            data["assets"] = updated_assets
            data["revision"] = character.revision + 1
            data["updated_at"] = utc_now()
            updated = Character.model_validate(data)
            self.characters._write(character_directory, updated)
            return updated

    def select_asset(
        self,
        project_id: UUID | str,
        character_id: UUID | str,
        asset_id: UUID | str | None,
        *,
        expected_revision: int,
    ) -> Character:
        expected_id = UUID(str(asset_id)) if asset_id is not None else None
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            character, character_directory = self._load_character_locked(
                project_directory, project_id, character_id
            )
            self._check_revision(character, expected_revision)
            if expected_id is not None and not any(
                asset.id == expected_id for asset in character.assets
            ):
                raise NotFoundError(f"asset '{expected_id}' was not found")
            data = character.model_dump()
            data["selected_asset_id"] = expected_id
            data["revision"] = character.revision + 1
            data["updated_at"] = utc_now()
            updated = Character.model_validate(data)
            self.characters._write(character_directory, updated)
            return updated

    def register_asset(
        self,
        project_id: UUID | str,
        character_id: UUID | str,
        *,
        expected_revision: int,
        asset: Asset,
        staged_content_path: Path,
        staged_thumbnail_path: Path | None = None,
    ) -> Character:
        project_directory = self.projects.path_for(project_id)
        published: list[Path] = []
        with project_lock(project_directory):
            character, character_directory = self._load_character_locked(
                project_directory, project_id, character_id
            )
            self._check_revision(character, expected_revision)
            content_path, thumbnail_path = self._publication_paths(
                project_directory, character, asset
            )
            if content_path.exists() or (thumbnail_path and thumbnail_path.exists()):
                raise ConflictError("asset destination already exists")
            if thumbnail_path is not None and staged_thumbnail_path is None:
                raise CorruptMetadataError("asset thumbnail staging path is required")

            try:
                os.replace(staged_content_path, content_path)
                published.append(content_path)
                if thumbnail_path is not None:
                    os.replace(staged_thumbnail_path, thumbnail_path)
                    published.append(thumbnail_path)
                data = character.model_dump()
                data["assets"] = [*character.assets, asset]
                data["revision"] = character.revision + 1
                data["updated_at"] = utc_now()
                updated = Character.model_validate(data)
                self.characters._write(character_directory, updated)
                return updated
            except Exception:
                for path in reversed(published):
                    path.unlink(missing_ok=True)
                raise

    def _load_character_locked(
        self,
        project_directory: Path,
        project_id: UUID | str,
        character_id: UUID | str,
    ) -> tuple[Character, Path]:
        expected_project_id = UUID(str(project_id))
        expected_character_id = UUID(str(character_id))
        project = self.projects._load(project_directory)
        if project.id != expected_project_id:
            raise NotFoundError(f"project '{expected_project_id}' was not found")
        reference = next(
            (item for item in project.characters if item.id == expected_character_id),
            None,
        )
        if reference is None:
            raise NotFoundError(f"character '{expected_character_id}' was not found")
        character_directory = resolve_within(
            project_directory, Path("characters") / reference.slug
        )
        character = self.characters._load_for_reference(
            project, reference, character_directory
        )
        return character, character_directory

    @staticmethod
    def _check_revision(character: Character, expected_revision: int) -> None:
        if character.revision != expected_revision:
            raise ConflictError(
                "La fiche a change sur disque; rechargez avant de sauver."
            )

    def _asset_paths(
        self,
        project_directory: Path,
        character: Character,
        asset: Asset,
    ) -> tuple[Path, Path | None]:
        if asset.kind != AssetKind.REFERENCE:
            raise CorruptMetadataError("asset is not a reference")
        content_relative = PurePosixPath(asset.relative_path)
        expected_parent = PurePosixPath(
            "characters", character.slug, "references"
        )
        if (
            content_relative.parent != expected_parent
            or content_relative.stem != str(asset.id)
            or content_relative.suffix not in {".png", ".jpg", ".webp"}
        ):
            raise CorruptMetadataError("reference path does not match its owner")
        thumbnail_relative = (
            PurePosixPath(asset.thumbnail_relative_path)
            if asset.thumbnail_relative_path is not None
            else None
        )
        if thumbnail_relative is not None and (
            thumbnail_relative.parent != PurePosixPath("thumbnails")
            or thumbnail_relative.name != f"{asset.id}.png"
        ):
            raise CorruptMetadataError("thumbnail path does not match its asset")

        content_directory = self._safe_directory(
            project_directory, content_relative.parent
        )
        content_path = self._safe_file_path(
            content_directory, content_relative.name
        )
        thumbnail_path = None
        if thumbnail_relative is not None:
            thumbnail_directory = self._safe_directory(
                project_directory, thumbnail_relative.parent
            )
            thumbnail_path = self._safe_file_path(
                thumbnail_directory, thumbnail_relative.name
            )
        return content_path, thumbnail_path

    def _publication_paths(
        self,
        project_directory: Path,
        character: Character,
        asset: Asset,
    ) -> tuple[Path, Path | None]:
        kind_directory = {
            AssetKind.GENERATION: "generations",
            AssetKind.UPSCALE: "upscales",
            AssetKind.EXPORT: "exports",
        }.get(asset.kind)
        if kind_directory is None:
            raise CorruptMetadataError("asset kind is not publishable")
        content_relative = PurePosixPath(asset.relative_path)
        expected_parent = PurePosixPath(
            "characters", character.slug, kind_directory
        )
        if (
            content_relative.parent != expected_parent
            or content_relative.stem != str(asset.id)
            or content_relative.suffix not in {".png", ".jpg", ".webp"}
        ):
            raise CorruptMetadataError("asset path does not match its owner")
        thumbnail_relative = (
            PurePosixPath(asset.thumbnail_relative_path)
            if asset.thumbnail_relative_path is not None
            else None
        )
        if thumbnail_relative is not None and (
            thumbnail_relative.parent != PurePosixPath("thumbnails")
            or thumbnail_relative.name != f"{asset.id}.png"
        ):
            raise CorruptMetadataError("thumbnail path does not match its asset")

        content_directory = self._safe_directory(
            project_directory, content_relative.parent
        )
        content_path = self._safe_file_path(
            content_directory, content_relative.name
        )
        thumbnail_path = None
        if thumbnail_relative is not None:
            thumbnail_directory = self._safe_directory(
                project_directory, thumbnail_relative.parent
            )
            thumbnail_path = self._safe_file_path(
                thumbnail_directory, thumbnail_relative.name
            )
        return content_path, thumbnail_path

    @staticmethod
    def _safe_file_path(directory: Path, filename: str) -> Path:
        lexical_path = directory / filename
        is_junction = getattr(lexical_path, "is_junction", lambda: False)
        if lexical_path.is_symlink() or is_junction():
            raise CorruptMetadataError(
                "asset file cannot be a symlink or junction"
            )
        return resolve_within(directory, filename)

    @staticmethod
    def _safe_directory(root: Path, relative: PurePosixPath) -> Path:
        current = root
        for part in relative.parts:
            current = current / part
            is_junction = getattr(current, "is_junction", lambda: False)
            if current.is_symlink() or is_junction():
                raise CorruptMetadataError(
                    "asset directory cannot be a symlink or junction"
                )
        resolved = resolve_within(root, Path(*relative.parts))
        if not resolved.is_dir():
            raise CorruptMetadataError("asset directory is missing")
        return resolved
