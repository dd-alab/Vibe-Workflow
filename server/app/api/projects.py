from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models import Project
from app.domain.validation import validate_slug
from app.services.project_service import ProjectService

from .dependencies import get_project_service

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    slug: str | None = None

    @field_validator("slug")
    @classmethod
    def slug_is_safe(cls, value: str | None) -> str | None:
        return validate_slug(value) if value is not None else None


class ProjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    notes_1: str | None = Field(default=None, max_length=12000)
    notes_2: str | None = Field(default=None, max_length=12000)

    @field_validator("name")
    @classmethod
    def name_has_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped


ProjectServiceDependency = Annotated[ProjectService, Depends(get_project_service)]


@router.get("", response_model=list[Project])
def list_projects(service: ProjectServiceDependency) -> list[Project]:
    return service.list_projects()


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    service: ProjectServiceDependency,
) -> Project:
    return service.create_project(payload.name, payload.slug)


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: UUID, service: ProjectServiceDependency) -> Project:
    return service.get_project(project_id)


@router.patch("/{project_id}", response_model=Project)
def update_project(
    project_id: UUID,
    payload: ProjectPatch,
    service: ProjectServiceDependency,
) -> Project:
    return service.update_project(
        project_id,
        expected_revision=payload.expected_revision,
        name=payload.name,
        notes_1=payload.notes_1,
        notes_2=payload.notes_2,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: UUID, service: ProjectServiceDependency) -> None:
    service.delete_project(project_id)
