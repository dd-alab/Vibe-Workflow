from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.repositories.asset_repository import AssetRepository
from app.repositories.character_repository import CharacterRepository
from app.repositories.job_repository import JobRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.run_repository import RunRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.services.asset_service import AssetService
from app.services.character_service import CharacterService
from app.services.connector_service import ConnectorService
from app.services.job_runner import JobRunner
from app.services.project_service import ProjectService
from app.services.run_service import RunService
from app.services.thumbnail_service import ThumbnailService
from app.services.workflow_executor import WorkflowExecutor
from app.services.workflow_service import WorkflowService
from app.services.workflow_validation import WorkflowValidator


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


def get_workflow_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkflowService:
    return WorkflowService(
        WorkflowRepository(settings.projects_root),
        WorkflowValidator(),
    )


def get_job_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JobRunner:
    return JobRunner(JobRepository(settings.projects_root))


def _workflow_executor(root) -> WorkflowExecutor:
    return WorkflowExecutor(
        JobRunner(JobRepository(root)),
        AssetRepository(root),
        WorkflowRepository(root),
    )


def get_run_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RunService:
    root = settings.projects_root
    return RunService(
        runs=RunRepository(root),
        jobs=JobRunner(JobRepository(root)),
        executor=_workflow_executor(root),
    )


def get_connector_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectorService:
    return ConnectorService()
