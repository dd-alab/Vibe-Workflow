import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from app.domain.models import Asset, AssetKind, Character
from app.repositories.asset_repository import AssetRepository

from .errors import (
    AssetFileMissingError,
    ServiceValidationError,
    UnsupportedMediaTypeError,
    UploadTooLargeError,
)
from .thumbnail_service import ThumbnailService

EXTENSION_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class AssetFile:
    path: Path
    media_type: str
    sha256: str | None = None


class AssetService:
    def __init__(
        self,
        assets: AssetRepository,
        thumbnails: ThumbnailService,
        *,
        max_reference_bytes: int,
    ) -> None:
        self.assets = assets
        self.thumbnails = thumbnails
        self.max_reference_bytes = max_reference_bytes

    def import_reference(
        self,
        project_id: UUID,
        character_id: UUID,
        *,
        expected_revision: int,
        filename: str | None,
        declared_media_type: str | None,
        source: BinaryIO,
    ) -> Character:
        extension, expected_media_type = self._validate_upload_identity(
            filename, declared_media_type
        )
        character = self.assets.get_character(project_id, character_id)
        asset_id = uuid4()
        with self.assets.staging_directory(project_id) as staging_directory:
            staged_content = staging_directory / "content.upload"
            digest = self._copy_and_hash(source, staged_content)
            staged_thumbnail = staging_directory / "thumbnail.png"
            image_info = self.thumbnails.inspect_and_create(
                staged_content, staged_thumbnail
            )
            if (
                image_info.media_type != expected_media_type
                or image_info.canonical_extension
                != (".jpg" if extension == ".jpeg" else extension)
            ):
                raise UnsupportedMediaTypeError(
                    "L'extension, le type declare et le contenu ne correspondent pas."
                )
            content_relative = (
                Path("characters")
                / character.slug
                / "references"
                / f"{asset_id}{image_info.canonical_extension}"
            ).as_posix()
            thumbnail_relative = (Path("thumbnails") / f"{asset_id}.png").as_posix()
            asset = Asset(
                id=asset_id,
                kind=AssetKind.REFERENCE,
                relative_path=content_relative,
                thumbnail_relative_path=thumbnail_relative,
                sha256=digest,
                media_type=image_info.media_type,
                width=image_info.width,
                height=image_info.height,
            )
            return self.assets.add_reference(
                project_id,
                character_id,
                expected_revision=expected_revision,
                asset=asset,
                staged_content_path=staged_content,
                staged_thumbnail_path=staged_thumbnail,
            )

    def get_content(self, asset_id: UUID | str) -> AssetFile:
        location = self.assets.locate(asset_id)
        if not location.content_path.is_file():
            raise AssetFileMissingError(location.asset.id, "content")
        return AssetFile(
            path=location.content_path,
            media_type=location.asset.media_type or "application/octet-stream",
            sha256=location.asset.sha256,
        )

    def get_thumbnail(self, asset_id: UUID | str) -> AssetFile:
        location = self.assets.locate(asset_id)
        if not location.content_path.is_file():
            raise AssetFileMissingError(location.asset.id, "content")
        if location.thumbnail_path is None or not location.thumbnail_path.is_file():
            raise AssetFileMissingError(location.asset.id, "thumbnail")
        return AssetFile(path=location.thumbnail_path, media_type="image/png")

    def delete_reference(
        self,
        project_id: UUID,
        character_id: UUID,
        asset_id: UUID,
        *,
        expected_revision: int,
    ) -> Character:
        return self.assets.delete_reference(
            project_id,
            character_id,
            asset_id,
            expected_revision=expected_revision,
        )

    def _copy_and_hash(self, source: BinaryIO, destination: Path) -> str:
        total = 0
        digest = hashlib.sha256()
        with destination.open("wb") as output:
            while chunk := source.read(1024 * 1024):
                total += len(chunk)
                if total > self.max_reference_bytes:
                    raise UploadTooLargeError(
                        "L'image depasse la taille maximale autorisee."
                    )
                output.write(chunk)
                digest.update(chunk)
            output.flush()
            os.fsync(output.fileno())
        return digest.hexdigest()

    @staticmethod
    def _validate_upload_identity(
        filename: str | None,
        declared_media_type: str | None,
    ) -> tuple[str, str]:
        if (
            not filename
            or filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
            or ":" in filename
            or any(ord(character) < 32 for character in filename)
        ):
            raise ServiceValidationError("Le nom du fichier est invalide.")
        extension = Path(filename).suffix.lower()
        expected_media_type = EXTENSION_MEDIA_TYPES.get(extension)
        if expected_media_type is None:
            raise UnsupportedMediaTypeError(
                "Seules les images PNG, JPEG et WebP sont acceptees."
            )
        normalized_media_type = (declared_media_type or "").split(";", 1)[0]
        normalized_media_type = normalized_media_type.strip().lower()
        if normalized_media_type != expected_media_type:
            raise UnsupportedMediaTypeError(
                "Le type declare ne correspond pas a l'extension du fichier."
            )
        return extension, expected_media_type
