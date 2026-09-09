from uuid import UUID

from app.domain.models import WorkflowRun
from app.repositories.run_repository import RunRepository

from .job_runner import JobRunner
from .workflow_executor import WorkflowExecutor


class RunService:
    def __init__(
        self,
        runs: RunRepository,
        jobs: JobRunner,
        executor: WorkflowExecutor,
    ) -> None:
        self.runs = runs
        self.jobs = jobs
        self.executor = executor

    def create_run(
        self,
        project_id: UUID,
        workflow_id: UUID,
        character_id: UUID,
    ) -> WorkflowRun:
        run = WorkflowRun(
            project_id=project_id,
            workflow_id=workflow_id,
            character_id=character_id,
        )
        run = self.runs.create(project_id, run)
        run = self.executor.execute(project_id, workflow_id, run)
        return self.runs.save(project_id, run)

    def get_run(self, project_id: UUID, run_id: UUID) -> WorkflowRun:
        return self.runs.get(project_id, run_id)

    def get_run_by_id(self, run_id: UUID) -> WorkflowRun:
        return self.runs.locate(run_id)

    def list_runs(self, project_id: UUID) -> list[WorkflowRun]:
        return self.runs.list_for_project(project_id)

    def recover_interrupted(self, project_id: UUID) -> list:
        return self.jobs.recover_interrupted(project_id)
