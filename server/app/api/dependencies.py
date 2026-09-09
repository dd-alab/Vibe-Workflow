from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.repositories.asset_repository import AssetRepository
from app.repositories.character_repository import CharacterRepository
from app.repositories.project_repository import ProjectRepository
from app.services.asset_service import AssetService
from app.services.character_service import CharacterService
from app.services.project_service import ProjectService
from app.services.thumbnail_service import ThumbnailService


def get_project_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProjectService:
    return ProjectService(ProjectRepository(settings.projects_root))


def get_character_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CharacterService:
    return CharacterService(CharacterRepository(settings.projects_root))


def get_asset_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssetService:
    return AssetService(
        AssetRepository(settings.projects_root),
        ThumbnailService(
            max_width=settings.max_reference_width,
            max_height=settings.max_reference_height,
            max_pixels=settings.max_reference_pixels,
            thumbnail_max_dimension=settings.thumbnail_max_dimension,
        ),
        max_reference_bytes=settings.max_reference_bytes,
    )
