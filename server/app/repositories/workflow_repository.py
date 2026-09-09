import json
import os
import shutil
import tempfile
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from app.domain.models import Workflow, utc_now
from app.storage.atomic_json import read_json, write_json_atomic
from app.storage.locks import project_lock
from app.storage.paths import ensure_internal_directory, resolve_within

from .errors import ConflictError, CorruptMetadataError, NotFoundError
from .project_repository import ProjectRepository


class WorkflowRepository:
    def __init__(self, root: Path) -> None:
        self.projects = ProjectRepository(root)

    def create(self, project_id: UUID | str, workflow: Workflow) -> Workflow:
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            workflow_directory = self._workflow_directory(
                project_directory, workflow.id
            )
            if workflow_directory.exists():
                raise ConflictError(
                    f"workflow '{workflow.id}' already exists"
                )
            self._ensure_workflows_root(project_directory)
            self._write_new(workflow_directory, workflow)
            return workflow

    def list_for_project(self, project_id: UUID | str) -> list[Workflow]:
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            workflows_root = resolve_within(project_directory, "workflows")
            workflows: list[Workflow] = []
            for workflow_file in sorted(
                workflows_root.glob("*/workflow.json")
            ):
                workflows.append(
                    self._load(workflow_file.parent)
                )
            return workflows

    def get(self, project_id: UUID | str, workflow_id: UUID | str) -> Workflow:
        expected_id = UUID(str(workflow_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            workflow_directory = self._workflow_directory(
                project_directory, expected_id
            )
            workflow = self._load(workflow_directory)
            if workflow.id != expected_id or workflow.project_id != UUID(
                str(project_id)
            ):
                raise CorruptMetadataError(
                    "workflow identity does not match its location"
                )
            return workflow

    def save(
        self, project_id: UUID | str, workflow: Workflow
    ) -> Workflow:
        expected_project_id = UUID(str(project_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            workflow_directory = self._workflow_directory(
                project_directory, workflow.id
            )
            if not workflow_directory.exists():
                raise NotFoundError(f"workflow '{workflow.id}' was not found")
            current = self._load(workflow_directory)
            if (
                current.id != workflow.id
                or current.project_id != workflow.project_id
                or current.project_id != expected_project_id
            ):
                raise ConflictError("workflow identity cannot be changed by save")
            updated = workflow.model_copy(
                update={"updated_at": utc_now()}
            )
            self._write(workflow_directory, updated)
            return updated

    def delete(self, project_id: UUID | str, workflow_id: UUID | str) -> None:
        expected_id = UUID(str(workflow_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            workflow_directory = self._workflow_directory(
                project_directory, expected_id
            )
            if not workflow_directory.exists():
                raise NotFoundError(f"workflow '{expected_id}' was not found")
            shutil.rmtree(workflow_directory)

    @staticmethod
    def metadata_path(workflow_directory: Path) -> Path:
        return workflow_directory / "workflow.json"

    def _ensure_workflows_root(self, project_directory: Path) -> None:
        ensure_internal_directory(project_directory, "workflows")

    def _workflow_directory(
        self, project_directory: Path, workflow_id: UUID | str
    ) -> Path:
        return resolve_within(
            project_directory, Path("workflows") / str(workflow_id)
        )

    def _load(self, workflow_directory: Path) -> Workflow:
        metadata_path = self.metadata_path(workflow_directory)
        if not metadata_path.exists():
            raise NotFoundError(
                f"workflow metadata is missing from '{workflow_directory.name}'"
            )
        try:
            return Workflow.model_validate(read_json(metadata_path))
        except (
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
            ValidationError,
            ValueError,
        ) as error:
            raise CorruptMetadataError("workflow metadata is invalid") from error

    def _write(self, workflow_directory: Path, workflow: Workflow) -> None:
        validated = Workflow.model_validate(workflow.model_dump(mode="json"))
        write_json_atomic(
            self.metadata_path(workflow_directory),
            validated.model_dump(mode="json"),
        )

    def _write_new(self, workflow_directory: Path, workflow: Workflow) -> None:
        staging_root = ensure_internal_directory(
            workflow_directory.parent, ".staging"
        )
        temporary_directory = Path(
            tempfile.mkdtemp(
                prefix=f".{workflow_directory.name}.",
                suffix=".tmp",
                dir=staging_root,
            )
        )
        try:
            self._write(temporary_directory, workflow)
            os.replace(str(temporary_directory), str(workflow_directory))
        finally:
            if temporary_directory.exists():
                shutil.rmtree(temporary_directory)
