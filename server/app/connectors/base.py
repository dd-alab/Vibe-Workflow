from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from app.domain.models import RunStatus
from app.domain.validation import redact_secrets


class ConnectorKind(str, Enum):
    GENERATION = "generation"
    UPSCALE = "upscale"


@dataclass(frozen=True)
class ConnectorContext:
    project_id: UUID
    run_id: UUID
    node_id: str
    character_id: UUID | None
    working_directory: Path
    inputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConnectorSubmission:
    external_id: str
    status: RunStatus = RunStatus.RUNNING
    output_path: Path | None = None
    error: str | None = None


@dataclass(frozen=True)
class ConnectorResult:
    output_path: Path
    media_type: str
    width: int = 0
    height: int = 0
    sha256: str | None = None


class Connector(ABC):
    """Minimal provider contract for generation and upscale connectors."""

    id: str
    kind: ConnectorKind

    @property
    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        """Static description of what the connector accepts and produces."""

    def validate(self, parameters: dict[str, Any]) -> None:
        """Raise ValueError when the parameters are not usable."""

    def estimate_cost(self, parameters: dict[str, Any]) -> float | None:
        return None

    def check(self) -> dict[str, Any]:
        return {"available": True}

    @abstractmethod
    def submit(
        self,
        parameters: dict[str, Any],
        context: ConnectorContext,
    ) -> ConnectorSubmission:
        """Start the remote work and return a submission handle."""

    def poll(self, submission: ConnectorSubmission) -> RunStatus:
        return submission.status

    def cancel(self, submission: ConnectorSubmission) -> None:
        return None

    @abstractmethod
    def fetch_results(self, submission: ConnectorSubmission) -> ConnectorResult:
        """Return the produced local file and its metadata."""

    def normalize_error(self, error: Exception) -> str:
        message = str(error) or "Erreur inconnue du connecteur."
        return redact_secrets(message)
