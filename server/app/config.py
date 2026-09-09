from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVER_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    projects_root: Path = Field(
        default=Path.home() / "VibeWorkflowProjects",
        validation_alias="PROJECTS_ROOT",
    )
    default_generation_connector: str = Field(
        default="mock-generation",
        validation_alias="DEFAULT_GENERATION_CONNECTOR",
    )
    default_upscale_connector: str = Field(
        default="mock-upscale",
        validation_alias="DEFAULT_UPSCALE_CONNECTOR",
    )
    max_reference_bytes: int = Field(
        default=25 * 1024 * 1024,
        gt=0,
        validation_alias="MAX_REFERENCE_BYTES",
    )
    max_reference_width: int = Field(
        default=16_384,
        gt=0,
        validation_alias="MAX_REFERENCE_WIDTH",
    )
    max_reference_height: int = Field(
        default=16_384,
        gt=0,
        validation_alias="MAX_REFERENCE_HEIGHT",
    )
    max_reference_pixels: int = Field(
        default=100_000_000,
        gt=0,
        validation_alias="MAX_REFERENCE_PIXELS",
    )
    thumbnail_max_dimension: int = Field(
        default=512,
        gt=0,
        validation_alias="THUMBNAIL_MAX_DIMENSION",
    )

    @field_validator("projects_root")
    @classmethod
    def normalize_projects_root(cls, value: Path) -> Path:
        expanded = value.expanduser()
        if not expanded.is_absolute():
            expanded = SERVER_ROOT / expanded
        return expanded.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
