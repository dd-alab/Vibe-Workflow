from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from app.domain.models import Project, utc_now
from app.storage.atomic_json import read_json, write_json_atomic
from app.storage.locks import project_lock
from app.storage.paths import (
    ensure_internal_directory,
    resolve_within,
    slugify,
    validate_slug,
)

from .errors import (
    ConflictError,
    CorruptMetadataError,
    NotFoundError,
    RepositoryError,
)

PROJECT_DIRECTORIES = (
    "characters",
    "jobs",
    "runs",
    "thumbnails",
    "workflows",
)


class ProjectRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.staging_root = ensure_internal_directory(self.root, ".staging")

    def create(self, name: str, slug: str | None = None) -> Project:
        project_slug = validate_slug(slug) if slug is not None else slugify(name)
        project_directory = resolve_within(self.root, project_slug)
        project = Project(name=name.strip(), slug=project_slug)

        with project_lock(project_directory):
            if project_directory.exists():
                raise ConflictError(f"project slug '{project_slug}' already exists")

            temporary_directory = Path(
                tempfile.mkdtemp(
                    prefix=f"{project_slug}.",
                    suffix=".tmp",
                    dir=self.staging_root,
                )
            )
            try:
                for directory_name in PROJECT_DIRECTORIES:
                    (temporary_directory / directory_name).mkdir()
                self._write(temporary_directory, project)
                os.replace(temporary_directory, project_directory)
            finally:
                if temporary_directory.exists():
                    shutil.rmtree(temporary_directory)
            return project

    def list(self) -> list[Project]:
        projects = []
        for project_file in self._project_files():
            project_directory = self._safe_project_directory(project_file)
            with project_lock(project_directory):
                projects.append(self._load(project_directory))
        return projects

    def get(self, project_id: UUID | str) -> Project:
        project_directory = self.path_for(project_id)
        with project_lock(project_directory):
            return self._load(project_directory)

    def path_for(self, project_id: UUID | str) -> Path:
        expected_id = UUID(str(project_id))
        corrupt_files = []
        for project_file in self._project_files():
            project_directory = self._safe_project_directory(project_file)
            try:
                with project_lock(project_directory):
                    project = Project.model_validate(read_json(project_file))
                    if project.id == expected_id:
                        return project_directory
            except CorruptMetadataError:
                corrupt_files.append(project_file)

        if corrupt_files:
            raise RepositoryError(
                f"project '{expected_id}' was not found; "
                f"{len(corrupt_files)} metadata file(s) could not be read"
            )
        raise NotFoundError(f"project '{expected_id}' was not found")

    def save(self, project: Project) -> Project:
        project_directory = self.path_for(project.id)
        with project_lock(project_directory):
            current = self._load(project_directory)
            if current.slug != project.slug:
                raise ConflictError("project identity cannot be changed by save")
            if current.revision != project.revision:
                raise ConflictError("project changed on disk; reload before saving")

            updated = project.model_copy(
                update={
                    "revision": project.revision + 1,
                    "updated_at": utc_now(),
                }
            )
            self._write(project_directory, updated)
            return updated

    @staticmethod
    def metadata_path(project_directory: Path) -> Path:
        return project_directory / "project.json"

    def _load(self, project_directory: Path) -> Project:
        try:
            data = read_json(self.metadata_path(project_directory))
            return Project.model_validate(data)
        except (
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
            ValidationError,
            ValueError,
        ) as error:
            raise CorruptMetadataError("project metadata is invalid") from error

    def _write(self, project_directory: Path, project: Project) -> None:
        validated = Project.model_validate(project.model_dump(mode="json"))
        write_json_atomic(
            self.metadata_path(project_directory), validated.model_dump(mode="json")
        )

    def _project_files(self) -> list[Path]:
        return sorted(
            project_file
            for project_file in self.root.glob("*/project.json")
            if not project_file.parent.name.startswith(".")
        )

    def _safe_project_directory(self, project_file: Path) -> Path:
        project_directory = project_file.parent
        is_junction = getattr(project_directory, "is_junction", lambda: False)
        if project_file.is_symlink() or project_directory.is_symlink() or is_junction():
            raise RepositoryError(
                f"project path '{project_directory}' points outside the projects root"
            )
        try:
            relative_directory = project_directory.relative_to(self.root)
            return resolve_within(self.root, relative_directory)
        except ValueError as error:
            raise RepositoryError(
                f"project path '{project_directory}' points outside the projects root"
            ) from error
