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
