from uuid import UUID

from app.domain.models import Project
from app.repositories.errors import ConflictError
from app.repositories.project_repository import ProjectRepository

from .errors import ServiceValidationError


class ProjectService:
    def __init__(self, projects: ProjectRepository) -> None:
        self.projects = projects

    def list_projects(self) -> list[Project]:
        return self.projects.list()

    def create_project(self, name: str, slug: str | None = None) -> Project:
        try:
            return self.projects.create(name=name, slug=slug)
        except ValueError as error:
            raise ServiceValidationError(
                "Le nom ne permet pas de creer un dossier projet valide."
            ) from error

    def get_project(self, project_id: UUID) -> Project:
        return self.projects.get(project_id)

    def update_project(
        self,
        project_id: UUID,
        *,
        expected_revision: int,
        name: str | None = None,
        notes_1: str | None = None,
        notes_2: str | None = None,
    ) -> Project:
        project = self.projects.get(project_id)
        self._check_revision(project.revision, expected_revision)
        data = project.model_dump()
        if name is not None:
            data["name"] = name.strip()
        if notes_1 is not None:
            data["notes_1"] = notes_1
        if notes_2 is not None:
            data["notes_2"] = notes_2
        return self.projects.save(Project.model_validate(data))

    def delete_project(self, project_id: UUID) -> None:
        self.projects.delete(project_id)

    @staticmethod
    def _check_revision(current: int, expected: int) -> None:
        if current != expected:
            raise ConflictError(
                "Le projet a change sur disque; veuillez recharger avant de sauver."
            )
