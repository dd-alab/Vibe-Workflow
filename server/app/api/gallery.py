from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.domain.models import Asset
from app.services.gallery_service import GalleryService

from .dependencies import get_gallery_service

router = APIRouter(tags=["gallery"])


class GalleryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    character_id: UUID
    character_name: str
    character_slug: str
    selected_asset: Asset | None


GalleryServiceDependency = Annotated[
    GalleryService, Depends(get_gallery_service)
]


@router.get("/projects/{project_id}/gallery", response_model=list[GalleryItemResponse])
def list_gallery(
    project_id: UUID,
    service: GalleryServiceDependency,
) -> list:
    return service.list_gallery(project_id)
