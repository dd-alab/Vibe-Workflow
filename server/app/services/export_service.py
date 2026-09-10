import hashlib
import shutil
from pathlib import Path, PurePosixPath
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.models import Asset, AssetKind, Character
from app.repositories.asset_repository import AssetRepository
from app.repositories.errors import ConflictError, NotFoundError

from .errors import AssetFileMissingError
from .thumbnail_service import ThumbnailService


class ExportService:
    def __init__(
        self,
        assets: AssetRepository,
        thumbnails: ThumbnailService,
    ) -> None:
        self.assets = assets
        self.thumbnails = thumbnails

    def export_selected(
        self,
        project_id: UUID,
        character_id: UUID,
        *,
        expected_revision: int,
    ) -> Character:
        character = self.assets.get_character(project_id, character_id)
        if character.selected_asset_id is None:
            raise NotFoundError("Aucune image selectionnee pour cet asset.")
        return self.export_asset(
            project_id,
            character_id,
            character.selected_asset_id,
            expected_revision=expected_revision,
        )

    def export_asset(
        self,
        project_id: UUID,
        character_id: UUID,
        asset_id: UUID,
        *,
        expected_revision: int,
    ) -> Character:
        character = self.assets.get_character(project_id, character_id)
        if any(asset.id == asset_id for asset in character.assets):
            source = self.assets.locate(asset_id)
        else:
            raise NotFoundError(f"asset '{asset_id}' was not found")
        if source.project_id != project_id or source.character_id != character_id:
            raise NotFoundError(f"asset '{asset_id}' was not found")
        if not source.content_path.is_file():
            raise AssetFileMissingError(source.asset.id, "content")

        export_id = uuid5(
            NAMESPACE_URL,
            f"vibe-workflow/export/{project_id}/{character_id}/{asset_id}",
        )
        if any(asset.id == export_id for asset in character.assets):
            raise ConflictError("Cet export existe deja pour cette image.")

        suffix = PurePosixPath(source.asset.relative_path).suffix or ".png"
        with self.assets.staging_directory(project_id) as staging_directory:
            staged_content = staging_directory / f"content{suffix}"
            digest = self._copy_and_hash(source.content_path, staged_content)
            staged_thumbnail = staging_directory / "thumbnail.png"
            if source.thumbnail_path is not None and source.thumbnail_path.is_file():
                shutil.copy2(source.thumbnail_path, staged_thumbnail)
            else:
                self.thumbnails.inspect_and_create(staged_content, staged_thumbnail)
            relative_path, thumbnail_relative_path = (
                self.assets.publication_relative_paths(
                    project_id,
                    export_id,
                    AssetKind.EXPORT,
                    suffix,
                )
            )
            export = Asset(
                id=export_id,
                kind=AssetKind.EXPORT,
                relative_path=relative_path,
                thumbnail_relative_path=thumbnail_relative_path,
                sha256=digest,
                media_type=source.asset.media_type,
                width=source.asset.width,
                height=source.asset.height,
            )
            return self.assets.register_asset(
                project_id,
                character_id,
                expected_revision=expected_revision,
                asset=export,
                staged_content_path=staged_content,
                staged_thumbnail_path=staged_thumbnail,
            )

    @staticmethod
    def _copy_and_hash(source: Path, destination: Path) -> str:
        digest = hashlib.sha256()
        with source.open("rb") as input_file, destination.open("wb") as output_file:
            while chunk := input_file.read(1024 * 1024):
                output_file.write(chunk)
                digest.update(chunk)
        return digest.hexdigest()
