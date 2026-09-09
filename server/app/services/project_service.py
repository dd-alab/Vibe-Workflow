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
        name: str,
    ) -> Project:
        project = self.projects.get(project_id)
        self._check_revision(project.revision, expected_revision)
        data = project.model_dump()
        data["name"] = name.strip()
        return self.projects.save(Project.model_validate(data))

    @staticmethod
    def _check_revision(current: int, expected: int) -> None:
        if current != expected:
            raise ConflictError(
                "Le projet a change sur disque; veuillez recharger avant de sauver."
            )
