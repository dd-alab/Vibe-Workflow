from pathlib import Path
from uuid import uuid4

from PIL import Image

from app.domain.models import RunStatus

from .base import (
    Connector,
    ConnectorContext,
    ConnectorKind,
    ConnectorResult,
    ConnectorSubmission,
)

MAX_SCALE = 4


class MockUpscaleConnector(Connector):
    id = "mock-upscale"
    kind = ConnectorKind.UPSCALE

    @property
    def capabilities(self) -> dict:
        return {
            "kind": "upscale",
            "inputs": ["image"],
            "parameters": ["scale"],
            "deterministic": True,
        }

    def validate(self, parameters: dict) -> None:
        scale = parameters.get("scale", 2)
        if not isinstance(scale, int) or scale <= 0:
            raise ValueError("scale must be a positive integer")
        if scale > MAX_SCALE:
            raise ValueError(f"scale cannot exceed {MAX_SCALE}")

    def submit(
        self,
        parameters: dict,
        context: ConnectorContext,
    ) -> ConnectorSubmission:
        self.validate(parameters)
        source_text = context.inputs.get("image")
        if not source_text:
            raise ValueError("upscale requires an input image")
        source_path = Path(source_text)
        if not source_path.is_file():
            raise ValueError("upscale input image is missing")
        scale = parameters.get("scale", 2)
        output_path = context.working_directory / f"{uuid4().hex}.png"
        with Image.open(source_path) as image:
            width, height = image.size
            upscaled = image.resize(
                (width * scale, height * scale),
                Image.Resampling.NEAREST,
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            upscaled.save(output_path, format="PNG")
        return ConnectorSubmission(
            external_id=uuid4().hex,
            status=RunStatus.COMPLETED,
            output_path=output_path,
        )

    def fetch_results(self, submission: ConnectorSubmission) -> ConnectorResult:
        path = submission.output_path
        with Image.open(path) as image:
            width, height = image.size
        return ConnectorResult(
            output_path=path,
            media_type="image/png",
            width=width,
            height=height,
        )
