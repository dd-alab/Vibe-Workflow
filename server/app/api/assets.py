from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.background import BackgroundTask

from app.domain.models import AssetClassification, Character
from app.services.asset_service import AssetService
from app.services.errors import AssetFileMissingError
from app.services.export_service import ExportService
from app.services.selection_service import SelectionService

from .dependencies import get_asset_service, get_export_service, get_selection_service

router = APIRouter(tags=["assets"])
AssetServiceDependency = Annotated[AssetService, Depends(get_asset_service)]
SelectionServiceDependency = Annotated[
    SelectionService, Depends(get_selection_service)
]
ExportServiceDependency = Annotated[ExportService, Depends(get_export_service)]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AssetPatch(StrictRequest):
    expected_revision: int = Field(ge=0)
    classification: AssetClassification


class SelectionUpdate(StrictRequest):
    expected_revision: int = Field(ge=0)
    asset_id: UUID | None = None


class ExportCreate(StrictRequest):
    expected_revision: int = Field(ge=0)
    asset_id: UUID | None = None


@router.post(
    "/projects/{project_id}/characters/{character_id}/references",
    response_model=Character,
    status_code=status.HTTP_201_CREATED,
)
def import_reference(
    project_id: UUID,
    character_id: UUID,
    service: AssetServiceDependency,
    expected_revision: Annotated[int, Form(ge=0)],
    file: Annotated[UploadFile, File()],
) -> Character:
    return service.import_reference(
        project_id,
        character_id,
        expected_revision=expected_revision,
        filename=file.filename,
        declared_media_type=file.content_type,
        source=file.file,
    )


@router.get("/assets/{asset_id}/content")
def get_asset_content(
    asset_id: UUID,
    service: AssetServiceDependency,
) -> StreamingResponse:
    asset_file = service.get_content(asset_id)
    headers = {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if asset_file.sha256:
        headers["ETag"] = f'"{asset_file.sha256}"'
    try:
        source = asset_file.path.open("rb")
    except OSError as error:
        raise AssetFileMissingError(asset_id, "content") from error
    return StreamingResponse(
        source,
        media_type=asset_file.media_type,
        headers=headers,
        background=BackgroundTask(source.close),
    )


@router.get("/assets/{asset_id}/thumbnail")
def get_asset_thumbnail(
    asset_id: UUID,
    service: AssetServiceDependency,
) -> StreamingResponse:
    asset_file = service.get_thumbnail(asset_id)
    try:
        source = asset_file.path.open("rb")
    except OSError as error:
        raise AssetFileMissingError(asset_id, "thumbnail") from error
    return StreamingResponse(
        source,
        media_type=asset_file.media_type,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
        background=BackgroundTask(source.close),
    )


@router.delete(
    "/projects/{project_id}/characters/{character_id}/references/{asset_id}",
    response_model=Character,
)
def delete_reference(
    project_id: UUID,
    character_id: UUID,
    asset_id: UUID,
    service: AssetServiceDependency,
    expected_revision: Annotated[int, Query(ge=0)],
) -> Character:
    return service.delete_reference(
        project_id,
        character_id,
        asset_id,
        expected_revision=expected_revision,
    )


@router.patch(
    "/projects/{project_id}/characters/{character_id}/assets/{asset_id}",
    response_model=Character,
)
def update_asset(
    project_id: UUID,
    character_id: UUID,
    asset_id: UUID,
    payload: AssetPatch,
    service: SelectionServiceDependency,
) -> Character:
    return service.classify_asset(
        project_id,
        character_id,
        asset_id,
        expected_revision=payload.expected_revision,
        classification=payload.classification,
    )


@router.post(
    "/projects/{project_id}/characters/{character_id}/selection",
    response_model=Character,
)
def select_asset(
    project_id: UUID,
    character_id: UUID,
    payload: SelectionUpdate,
    service: SelectionServiceDependency,
) -> Character:
    return service.select_asset(
        project_id,
        character_id,
        payload.asset_id,
        expected_revision=payload.expected_revision,
    )


@router.post(
    "/projects/{project_id}/characters/{character_id}/exports",
    response_model=Character,
    status_code=status.HTTP_201_CREATED,
)
def export_asset(
    project_id: UUID,
    character_id: UUID,
    payload: ExportCreate,
    service: ExportServiceDependency,
) -> Character:
    if payload.asset_id is None:
        return service.export_selected(
            project_id,
            character_id,
            expected_revision=payload.expected_revision,
        )
    return service.export_asset(
        project_id,
        character_id,
        payload.asset_id,
        expected_revision=payload.expected_revision,
    )
