import json
import os
import shutil
import tempfile
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from app.domain.models import Job, utc_now
from app.storage.atomic_json import read_json, write_json_atomic
from app.storage.locks import project_lock
from app.storage.paths import ensure_internal_directory, resolve_within

from .errors import ConflictError, CorruptMetadataError, NotFoundError
from .project_repository import ProjectRepository


class JobRepository:
    def __init__(self, root: Path) -> None:
        self.projects = ProjectRepository(root)

    def create(self, project_id: UUID | str, job: Job) -> Job:
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            job_directory = self._job_directory(project_directory, job.id)
            if job_directory.exists():
                raise ConflictError(f"job '{job.id}' already exists")
            ensure_internal_directory(project_directory, "jobs")
            self._write_new(job_directory, job)
            return job

    def get(self, project_id: UUID | str, job_id: UUID | str) -> Job:
        expected_id = UUID(str(job_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            job_directory = self._job_directory(project_directory, expected_id)
            job = self._load(job_directory)
            if job.id != expected_id or job.project_id != UUID(str(project_id)):
                raise CorruptMetadataError("job identity does not match its location")
            return job

    def save(self, project_id: UUID | str, job: Job) -> Job:
        expected_project_id = UUID(str(project_id))
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            job_directory = self._job_directory(project_directory, job.id)
            if not job_directory.exists():
                raise NotFoundError(f"job '{job.id}' was not found")
            current = self._load(job_directory)
            if (
                current.id != job.id
                or current.project_id != job.project_id
                or current.project_id != expected_project_id
            ):
                raise ConflictError("job identity cannot be changed by save")
            updated = job.model_copy(update={"updated_at": utc_now()})
            self._write(job_directory, updated)
            return updated

    def list_for_project(self, project_id: UUID | str) -> list[Job]:
        project_directory = self.projects.path_for(project_id)
        with project_lock(project_directory):
            jobs_root = resolve_within(project_directory, "jobs")
            return [
                self._load(path.parent)
                for path in sorted(jobs_root.glob("*/job.json"))
            ]

    def locate(self, job_id: UUID | str) -> Job:
        expected_id = UUID(str(job_id))
        for project in self.projects.list():
            project_directory = self.projects.path_for(project.id)
            job_directory = resolve_within(
                project_directory, Path("jobs") / str(expected_id)
            )
            if not job_directory.exists():
                continue
            with project_lock(project_directory):
                job = self._load(job_directory)
                if job.id == expected_id:
                    return job
        raise NotFoundError(f"job '{expected_id}' was not found")

    @staticmethod
    def metadata_path(job_directory: Path) -> Path:
        return job_directory / "job.json"

    def _job_directory(self, project_directory: Path, job_id: UUID | str) -> Path:
        return resolve_within(project_directory, Path("jobs") / str(job_id))

    def _load(self, job_directory: Path) -> Job:
        metadata_path = self.metadata_path(job_directory)
        if not metadata_path.exists():
            raise NotFoundError(f"job metadata is missing from '{job_directory.name}'")
        try:
            return Job.model_validate(read_json(metadata_path))
        except (
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
            ValidationError,
            ValueError,
        ) as error:
            raise CorruptMetadataError("job metadata is invalid") from error

    def _write(self, job_directory: Path, job: Job) -> None:
        validated = Job.model_validate(job.model_dump(mode="json"))
        write_json_atomic(
            self.metadata_path(job_directory),
            validated.model_dump(mode="json"),
        )

    def _write_new(self, job_directory: Path, job: Job) -> None:
        staging_root = ensure_internal_directory(job_directory.parent, ".staging")
        temporary_directory = Path(
            tempfile.mkdtemp(
                prefix=f".{job_directory.name}.",
                suffix=".tmp",
                dir=staging_root,
            )
        )
        try:
            self._write(temporary_directory, job)
            os.replace(str(temporary_directory), str(job_directory))
        finally:
            if temporary_directory.exists():
                shutil.rmtree(temporary_directory)
