from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

from .validation import (
    ensure_no_secrets,
    redact_secrets,
    validate_relative_path,
    validate_slug,
)

SCHEMA_VERSION = 1


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return value.astimezone(timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(normalize_timestamp)]


class DomainModel(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        validate_assignment=True,
    )

    @model_serializer(mode="wrap")
    def serialize_without_secrets(self, handler):
        serialized = handler(self)
        ensure_no_secrets(serialized)
        return serialized


class CharacterReference(DomainModel):
    id: UUID
    slug: str

    @field_validator("slug")
    @classmethod
    def slug_is_safe(cls, value: str) -> str:
        return validate_slug(value)


class Project(DomainModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=120)
    slug: str
    revision: int = Field(default=0, ge=0)
    characters: list[CharacterReference] = Field(default_factory=list)
    created_at: UtcDatetime = Field(default_factory=utc_now)
    updated_at: UtcDatetime = Field(default_factory=utc_now)

    @field_validator("slug")
    @classmethod
    def slug_is_safe(cls, value: str) -> str:
        return validate_slug(value)

    @model_validator(mode="after")
    def character_references_are_unique(self):
        ids = [reference.id for reference in self.characters]
        slugs = [reference.slug for reference in self.characters]
        if len(ids) != len(set(ids)) or len(slugs) != len(set(slugs)):
            raise ValueError("character references must have unique ids and slugs")
        return self


class TextBlock(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    text: str = Field(min_length=1, max_length=1000)
    created_at: UtcDatetime = Field(default_factory=utc_now)
    updated_at: UtcDatetime = Field(default_factory=utc_now)


class PromptBlock(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=4000)
    created_at: UtcDatetime = Field(default_factory=utc_now)
    updated_at: UtcDatetime = Field(default_factory=utc_now)


class PromptVersion(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    text: str = Field(min_length=1, max_length=12000)
    block_ids: list[UUID] = Field(default_factory=list)
    created_at: UtcDatetime = Field(default_factory=utc_now)


class AssetKind(str, Enum):
    REFERENCE = "reference"
    GENERATION = "generation"
    UPSCALE = "upscale"
    EXPORT = "export"


class AssetClassification(str, Enum):
    NEUTRAL = "neutral"
    FAVORITE = "favorite"
    REJECTED = "rejected"


class Asset(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    kind: AssetKind
    relative_path: str
    thumbnail_relative_path: str | None = None
    classification: AssetClassification = AssetClassification.NEUTRAL
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    media_type: str | None = None
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    created_at: UtcDatetime = Field(default_factory=utc_now)

    @field_validator("relative_path", "thumbnail_relative_path")
    @classmethod
    def paths_are_relative(cls, value: str | None) -> str | None:
        return validate_relative_path(value) if value is not None else None


class Character(DomainModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    name: str = Field(min_length=1, max_length=120)
    slug: str
    revision: int = Field(default=0, ge=0)
    short_texts: list[TextBlock] = Field(default_factory=list)
    prompt_blocks: list[PromptBlock] = Field(default_factory=list)
    prompt_versions: list[PromptVersion] = Field(default_factory=list)
    active_prompt_version_id: UUID | None = None
    assets: list[Asset] = Field(default_factory=list)
    selected_asset_id: UUID | None = None
    created_at: UtcDatetime = Field(default_factory=utc_now)
    updated_at: UtcDatetime = Field(default_factory=utc_now)

    @field_validator("slug")
    @classmethod
    def slug_is_safe(cls, value: str) -> str:
        return validate_slug(value)

    @model_validator(mode="after")
    def references_are_consistent(self):
        text_ids = [text.id for text in self.short_texts]
        prompt_ids = [prompt.id for prompt in self.prompt_versions]
        block_ids = [block.id for block in self.prompt_blocks]
        asset_ids = [asset.id for asset in self.assets]
        collections = (text_ids, prompt_ids, block_ids, asset_ids)
        if any(len(values) != len(set(values)) for values in collections):
            raise ValueError("character collections must have unique ids")
        if (
            self.active_prompt_version_id is not None
            and self.active_prompt_version_id not in prompt_ids
        ):
            raise ValueError("active prompt must reference an existing prompt version")
        if (
            self.selected_asset_id is not None
            and self.selected_asset_id not in asset_ids
        ):
            raise ValueError("selected asset must reference an existing asset")
        known_block_ids = set(block_ids)
        if any(
            len(prompt.block_ids) != len(set(prompt.block_ids))
            for prompt in self.prompt_versions
        ):
            raise ValueError("prompt versions cannot contain duplicate prompt blocks")
        if any(
            block_id not in known_block_ids
            for prompt in self.prompt_versions
            for block_id in prompt.block_ids
        ):
            raise ValueError("prompt versions must reference existing prompt blocks")
        return self


class WorkflowPosition(DomainModel):
    x: float = 0
    y: float = 0


class WorkflowNode(DomainModel):
    id: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=120)
    version: int = Field(default=1, ge=1)
    position: WorkflowPosition = Field(default_factory=WorkflowPosition)
    connector_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("parameters")
    @classmethod
    def parameters_contain_no_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_no_secrets(value)


class WorkflowEdge(DomainModel):
    id: str = Field(min_length=1, max_length=120)
    source_node_id: str = Field(min_length=1, max_length=120)
    source_port: str = Field(min_length=1, max_length=120)
    target_node_id: str = Field(min_length=1, max_length=120)
    target_port: str = Field(min_length=1, max_length=120)


class Workflow(DomainModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    name: str = Field(min_length=1, max_length=120)
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    created_at: UtcDatetime = Field(default_factory=utc_now)
    updated_at: UtcDatetime = Field(default_factory=utc_now)


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowRun(DomainModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    workflow_id: UUID
    character_id: UUID | None = None
    status: RunStatus = RunStatus.QUEUED
    job_ids: list[UUID] = Field(default_factory=list)
    created_at: UtcDatetime = Field(default_factory=utc_now)
    updated_at: UtcDatetime = Field(default_factory=utc_now)


class Job(DomainModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    workflow_id: UUID
    character_id: UUID | None = None
    connector_id: str = Field(min_length=1, max_length=120)
    status: RunStatus = RunStatus.QUEUED
    parameters: dict[str, Any] = Field(default_factory=dict)
    output_asset_ids: list[UUID] = Field(default_factory=list)
    previous_attempt_id: UUID | None = None
    error: str | None = None
    created_at: UtcDatetime = Field(default_factory=utc_now)
    updated_at: UtcDatetime = Field(default_factory=utc_now)

    @field_validator("parameters")
    @classmethod
    def parameters_contain_no_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_no_secrets(value)

    @field_validator("error")
    @classmethod
    def error_redacts_secrets(cls, value: str | None) -> str | None:
        return redact_secrets(value) if value is not None else None
