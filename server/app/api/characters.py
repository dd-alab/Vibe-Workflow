from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.models import Character
from app.domain.validation import validate_slug
from app.services.character_service import (
    CharacterService,
    PromptBlockChange,
    TextBlockChange,
)

from .dependencies import get_character_service

router = APIRouter(
    prefix="/projects/{project_id}/characters",
    tags=["characters"],
)


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CharacterCreate(StrictRequest):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = None

    @field_validator("slug")
    @classmethod
    def slug_is_safe(cls, value: str | None) -> str | None:
        return validate_slug(value) if value is not None else None


class TextBlockInput(StrictRequest):
    id: UUID | None = None
    text: str = Field(min_length=1, max_length=1000)


class PromptBlockInput(StrictRequest):
    id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=4000)


class CharacterPatch(StrictRequest):
    expected_revision: int = Field(ge=0)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    short_texts: list[TextBlockInput] | None = None
    prompt_blocks: list[PromptBlockInput] | None = None

    @model_validator(mode="after")
    def supplied_ids_are_unique(self):
        for collection in (self.short_texts, self.prompt_blocks):
            if collection is None:
                continue
            ids = [item.id for item in collection if item.id is not None]
            if len(ids) != len(set(ids)):
                raise ValueError("collection ids must be unique")
        return self


class PromptCreate(StrictRequest):
    expected_revision: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=12000)
    block_ids: list[UUID] = Field(default_factory=list)

    @field_validator("block_ids")
    @classmethod
    def block_ids_are_unique(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("prompt block ids must be unique")
        return value


class PromptActivate(StrictRequest):
    expected_revision: int = Field(ge=0)


CharacterServiceDependency = Annotated[
    CharacterService, Depends(get_character_service)
]


@router.get("", response_model=list[Character])
def list_characters(
    project_id: UUID,
    service: CharacterServiceDependency,
) -> list[Character]:
    return service.list_characters(project_id)


@router.post("", response_model=Character, status_code=status.HTTP_201_CREATED)
def create_character(
    project_id: UUID,
    payload: CharacterCreate,
    service: CharacterServiceDependency,
) -> Character:
    return service.create_character(project_id, payload.name, payload.slug)


@router.get("/{character_id}", response_model=Character)
def get_character(
    project_id: UUID,
    character_id: UUID,
    service: CharacterServiceDependency,
) -> Character:
    return service.get_character(project_id, character_id)


@router.patch("/{character_id}", response_model=Character)
def update_character(
    project_id: UUID,
    character_id: UUID,
    payload: CharacterPatch,
    service: CharacterServiceDependency,
) -> Character:
    short_texts = (
        [TextBlockChange(id=item.id, text=item.text) for item in payload.short_texts]
        if payload.short_texts is not None
        else None
    )
    prompt_blocks = (
        [
            PromptBlockChange(id=item.id, name=item.name, text=item.text)
            for item in payload.prompt_blocks
        ]
        if payload.prompt_blocks is not None
        else None
    )
    return service.update_character(
        project_id,
        character_id,
        expected_revision=payload.expected_revision,
        name=payload.name,
        short_texts=short_texts,
        prompt_blocks=prompt_blocks,
    )


@router.post(
    "/{character_id}/prompts",
    response_model=Character,
    status_code=status.HTTP_201_CREATED,
)
def create_prompt(
    project_id: UUID,
    character_id: UUID,
    payload: PromptCreate,
    service: CharacterServiceDependency,
) -> Character:
    return service.create_prompt(
        project_id,
        character_id,
        expected_revision=payload.expected_revision,
        text=payload.text,
        block_ids=payload.block_ids,
    )


@router.post("/{character_id}/prompts/{prompt_id}/activate", response_model=Character)
def activate_prompt(
    project_id: UUID,
    character_id: UUID,
    prompt_id: UUID,
    payload: PromptActivate,
    service: CharacterServiceDependency,
) -> Character:
    return service.activate_prompt(
        project_id,
        character_id,
        prompt_id,
        expected_revision=payload.expected_revision,
    )
