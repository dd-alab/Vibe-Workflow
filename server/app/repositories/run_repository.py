import json
import os
import shutil
import tempfile
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from app.domain.models import WorkflowRun, utc_now
from app.storage.atomic_json import read_json, write_json_atomic
from app.storage.locks import project_lock
from app.storage.paths import ensure_internal_directory, resolve_within

from .errors import ConflictError, CorruptMetadataError, NotFoundError
from .project_repository import ProjectRepository


class RunRepository:
    def __init__(self, root: Path) -> None:
        self.projects = ProjectRepository(root)

    def create(self, project_id: UUID | str, run: WorkflowRun) -> WorkflowRun:
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            run_directory = self._run_directory(project_directory, run.id)
            if run_directory.exists():
                raise ConflictError(f"run '{run.id}' already exists")
            ensure_internal_directory(project_directory, "runs")
            self._write_new(run_directory, run)
            return run

    def get(self, project_id: UUID | str, run_id: UUID | str) -> WorkflowRun:
        expected_id = UUID(str(run_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            run_directory = self._run_directory(project_directory, expected_id)
            run = self._load(run_directory)
            if run.id != expected_id or run.project_id != UUID(str(project_id)):
                raise CorruptMetadataError("run identity does not match its location")
            return run

    def save(self, project_id: UUID | str, run: WorkflowRun) -> WorkflowRun:
        expected_project_id = UUID(str(project_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            run_directory = self._run_directory(project_directory, run.id)
            if not run_directory.exists():
                raise NotFoundError(f"run '{run.id}' was not found")
            current = self._load(run_directory)
            if (
                current.id != run.id
                or current.project_id != run.project_id
                or current.project_id != expected_project_id
            ):
                raise ConflictError("run identity cannot be changed by save")
            updated = run.model_copy(update={"updated_at": utc_now()})
            self._write(run_directory, updated)
            return updated

    @staticmethod
    def metadata_path(run_directory: Path) -> Path:
        return run_directory / "run.json"

    def list_for_project(self, project_id: UUID | str) -> list[WorkflowRun]:
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            runs_root = resolve_within(project_directory, "runs")
            return [
                self._load(path.parent)
                for path in sorted(runs_root.glob("*/run.json"))
            ]

    def locate(self, run_id: UUID | str) -> WorkflowRun:
        expected_id = UUID(str(run_id))
        for project in self.projects.list():
            project_directory = self.projects.path_for(project.id)
            run_directory = resolve_within(
                project_directory, Path("runs") / str(expected_id)
            )
            if not run_directory.exists():
                continue
            with project_lock(project_directory):
                run = self._load(run_directory)
                if run.id == expected_id:
                    return run
        raise NotFoundError(f"run '{expected_id}' was not found")

    def _run_directory(self, project_directory: Path, run_id: UUID | str) -> Path:
        return resolve_within(project_directory, Path("runs") / str(run_id))

    def _load(self, run_directory: Path) -> WorkflowRun:
        metadata_path = self.metadata_path(run_directory)
        if not metadata_path.exists():
            raise NotFoundError(f"run metadata is missing from '{run_directory.name}'")
        try:
            return WorkflowRun.model_validate(read_json(metadata_path))
        except (
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
            ValidationError,
            ValueError,
        ) as error:
            raise CorruptMetadataError("run metadata is invalid") from error

    def _write(self, run_directory: Path, run: WorkflowRun) -> None:
        validated = WorkflowRun.model_validate(run.model_dump(mode="json"))
        write_json_atomic(
            self.metadata_path(run_directory),
            validated.model_dump(mode="json"),
        )

    def _write_new(self, run_directory: Path, run: WorkflowRun) -> None:
        staging_root = ensure_internal_directory(run_directory.parent, ".staging")
        temporary_directory = Path(
            tempfile.mkdtemp(
                prefix=f".{run_directory.name}.",
                suffix=".tmp",
                dir=staging_root,
            )
        )
        try:
            self._write(temporary_directory, run)
            os.replace(str(temporary_directory), str(run_directory))
        finally:
            if temporary_directory.exists():
                shutil.rmtree(temporary_directory)
