from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.repositories.character_repository import CharacterRepository
from app.repositories.project_repository import ProjectRepository
from app.services.character_service import CharacterService
from app.services.project_service import ProjectService


def get_project_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProjectService:
    return ProjectService(ProjectRepository(settings.projects_root))


def get_character_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CharacterService:
    return CharacterService(CharacterRepository(settings.projects_root))
