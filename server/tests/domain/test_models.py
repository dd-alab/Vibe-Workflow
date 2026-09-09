from datetime import datetime
from math import nan
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.models import (
    Asset,
    AssetKind,
    Character,
    Job,
    Project,
    PromptBlock,
    PromptVersion,
    WorkflowNode,
)


def test_asset_paths_are_portable() -> None:
    asset = Asset(
        kind=AssetKind.REFERENCE,
        relative_path="characters/auguste/references/portrait.png",
    )

    assert asset.relative_path == "characters/auguste/references/portrait.png"


def test_asset_rejects_absolute_path() -> None:
    with pytest.raises(ValidationError):
        Asset(kind=AssetKind.REFERENCE, relative_path="C:\\portrait.png")


def test_project_rejects_unsupported_schema_version() -> None:
    with pytest.raises(ValidationError):
        Project(name="Circus", slug="circus", schema_version=2)


def test_project_rejects_invalid_slug_when_loading_json() -> None:
    with pytest.raises(ValidationError):
        Project(name="Circus", slug="../circus")


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            WorkflowNode,
            {
                "id": "generate",
                "type": "image-generation-api",
                "parameters": {"api_key": "sentinel-secret"},
            },
        ),
        (
            Job,
            {
                "project_id": uuid4(),
                "workflow_id": uuid4(),
                "connector_id": "mock-generation",
                "parameters": {"authorization": "sentinel-secret"},
            },
        ),
        (
            WorkflowNode,
            {
                "id": "generate",
                "type": "image-generation-api",
                "parameters": {"secretAccessKey": "sentinel-secret"},
            },
        ),
    ],
)
def test_serializable_models_reject_secrets(model, payload) -> None:
    with pytest.raises(ValidationError, match="secret"):
        model(**payload)


def test_character_rejects_dangling_active_prompt() -> None:
    with pytest.raises(ValidationError, match="active prompt"):
        Character(
            project_id=uuid4(),
            name="Auguste",
            slug="auguste",
            prompt_versions=[PromptVersion(text="Portrait")],
            active_prompt_version_id=uuid4(),
        )


def test_project_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        Project(
            name="Circus",
            slug="circus",
            created_at=datetime(2026, 9, 8),
        )


def test_workflow_node_rejects_non_finite_parameter() -> None:
    with pytest.raises(ValidationError, match="non-finite"):
        WorkflowNode(
            id="generate",
            type="image-generation-api",
            parameters={"guidance": nan},
        )


def test_job_error_redacts_common_secret_formats() -> None:
    job = Job(
        project_id=uuid4(),
        workflow_id=uuid4(),
        connector_id="mock-generation",
        error="provider failed api_key=abc123 Authorization: Bearer-456 Bearer xyz789",
    )

    assert "abc123" not in job.error
    assert "Bearer-456" not in job.error
    assert "xyz789" not in job.error


def test_character_rejects_duplicate_prompt_block_reference() -> None:
    block = PromptBlock(name="Lighting", text="Dramatic light")

    with pytest.raises(ValidationError, match="duplicate prompt blocks"):
        Character(
            project_id=uuid4(),
            name="Auguste",
            slug="auguste",
            prompt_blocks=[block],
            prompt_versions=[
                PromptVersion(text="Portrait", block_ids=[block.id, block.id])
            ],
        )
