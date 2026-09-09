import hashlib
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw

from app.domain.models import RunStatus

from .base import (
    Connector,
    ConnectorContext,
    ConnectorKind,
    ConnectorResult,
    ConnectorSubmission,
)

MAX_DIMENSION = 2048


def _color(seed_text: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    return (digest[0] % 256, digest[1] % 256, digest[2] % 256)


def _create_generation_png(
    path: Path, width: int, height: int, seed_text: str
) -> tuple[int, int]:
    color = _color(seed_text)
    image = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(image)
    step = max(2, min(width, height) // 12)
    for index in range(1, 12):
        offset = index * step
        if offset * 2 >= width and offset * 2 >= height:
            break
        shade = tuple((channel + offset) % 256 for channel in color)
        draw.rectangle(
            (offset, offset, width - offset, height - offset),
            outline=shade,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return width, height


class MockGenerationConnector(Connector):
    id = "mock-generation"
    kind = ConnectorKind.GENERATION

    @property
    def capabilities(self) -> dict:
        return {
            "kind": "generation",
            "inputs": ["prompt"],
            "parameters": ["width", "height", "seed"],
            "deterministic": True,
        }

    def validate(self, parameters: dict) -> None:
        width = parameters.get("width")
        height = parameters.get("height")
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("width and height must be integers")
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            raise ValueError(f"dimensions exceed {MAX_DIMENSION}")

    def submit(
        self,
        parameters: dict,
        context: ConnectorContext,
    ) -> ConnectorSubmission:
        self.validate(parameters)
        width = parameters.get("width", 1024)
        height = parameters.get("height", 1024)
        seed = parameters.get("seed")
        prompt = context.inputs.get("prompt", "")
        seed_text = f"{prompt}|{seed}|{width}|{height}"
        output_path = context.working_directory / f"{uuid4().hex}.png"
        _create_generation_png(output_path, width, height, seed_text)
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
