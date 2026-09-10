import logging
from pathlib import Path
from uuid import UUID

from app.connectors import ConnectorContext, get_connector
from app.domain.jobs import raise_on_invalid_transition
from app.domain.models import Job, RunStatus, utc_now
from app.repositories.job_repository import JobRepository

from .errors import ServiceValidationError

logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, jobs: JobRepository) -> None:
        self.jobs = jobs

    def create_job(
        self,
        project_id: UUID,
        *,
        workflow_id: UUID,
        run_id: UUID | None,
        node_id: str | None,
        character_id: UUID | None,
        connector_id: str,
        parameters: dict,
        inputs: dict | None = None,
        previous_attempt_id: UUID | None = None,
    ) -> Job:
        job = Job(
            project_id=project_id,
            workflow_id=workflow_id,
            run_id=run_id,
            node_id=node_id,
            character_id=character_id,
            connector_id=connector_id,
            parameters=parameters,
            inputs=inputs or {},
            previous_attempt_id=previous_attempt_id,
        )
        return self.jobs.create(project_id, job)

    def get_job(self, project_id: UUID, job_id: UUID) -> Job:
        return self.jobs.get(project_id, job_id)

    def get_job_by_id(self, job_id: UUID) -> Job:
        return self.jobs.locate(job_id)

    def list_jobs(self, project_id: UUID) -> list[Job]:
        return self.jobs.list_for_project(project_id)

    def cancel_job_by_id(self, job_id: UUID) -> Job:
        job = self.jobs.locate(job_id)
        return self.cancel_job(job.project_id, job.id)

    def retry_by_id(self, job_id: UUID) -> Job:
        job = self.jobs.locate(job_id)
        return self.retry(job.project_id, job.id)

    def add_output_asset(
        self,
        project_id: UUID,
        job_id: UUID,
        asset_id: UUID,
    ) -> Job:
        job = self.jobs.get(project_id, job_id)
        if asset_id in job.output_asset_ids:
            return job
        updated = job.model_copy(
            update={
                "output_asset_ids": [*job.output_asset_ids, asset_id],
                "updated_at": utc_now(),
            }
        )
        return self._save(project_id, updated)

    def cancel_job(self, project_id: UUID, job_id: UUID) -> Job:
        job = self.jobs.get(project_id, job_id)
        if job.status not in (RunStatus.QUEUED, RunStatus.RUNNING):
            raise ServiceValidationError(
                "Un travail termine ne peut pas etre annule."
            )
        updated = self._transition(job, RunStatus.CANCELLED)
        return self._save(project_id, updated)

    def retry(self, project_id: UUID, job_id: UUID) -> Job:
        job = self.jobs.get(project_id, job_id)
        if job.status not in (RunStatus.FAILED, RunStatus.CANCELLED):
            raise ServiceValidationError(
                "Seul un travail echoue ou annule peut etre relance."
            )
        new_job = self.create_job(
            project_id,
            workflow_id=job.workflow_id,
            run_id=job.run_id,
            node_id=job.node_id,
            character_id=job.character_id,
            connector_id=job.connector_id,
            parameters=job.parameters,
            inputs=job.inputs,
            previous_attempt_id=job.id,
        )
        self.run_job(project_id, new_job)
        return self.jobs.get(project_id, new_job.id)

    def run_job(self, project_id: UUID, job: Job):

        connector = get_connector(job.connector_id)
        project_directory = self.jobs.projects.path_for(project_id)
        working_directory = self._working_directory(project_directory, job.id)
        context = ConnectorContext(
            project_id=project_id,
            run_id=job.run_id,
            node_id=job.node_id or "",
            character_id=job.character_id,
            working_directory=working_directory,
            inputs=job.inputs,
        )
        running = self._transition(job, RunStatus.RUNNING)
        running = self._save(project_id, running)
        logger.info(
            "job started id=%s connector=%s node=%s run=%s",
            job.id,
            job.connector_id,
            job.node_id,
            job.run_id,
        )
        try:
            submission = connector.submit(job.parameters, context)
            status = connector.poll(submission)
            if status != RunStatus.COMPLETED:
                raise RuntimeError("le connecteur n'a pas produit de resultat")
            result = connector.fetch_results(submission)
            output_paths = self._relative(project_directory, result.output_path)
            updated = self._transition(running, RunStatus.COMPLETED)
            updated = updated.model_copy(
                update={
                    "output_paths": [output_paths],
                    "updated_at": utc_now(),
                }
            )
            self._save(project_id, updated)
            logger.info(
                "job completed id=%s connector=%s output=%s",
                job.id,
                job.connector_id,
                output_paths,
            )
            return result
        except Exception as error:
            message = connector.normalize_error(error)
            failed = self._transition(running, RunStatus.FAILED)
            failed = failed.model_copy(
                update={"error": message, "updated_at": utc_now()}
            )
            self._save(project_id, failed)
            logger.exception(
                "job failed id=%s connector=%s node=%s error=%s",
                job.id,
                job.connector_id,
                job.node_id,
                message,
            )
            raise

    def recover_interrupted(self, project_id: UUID) -> list[Job]:
        recovered: list[Job] = []
        for job in self.list_jobs(project_id):
            if job.status in (RunStatus.QUEUED, RunStatus.RUNNING):
                failed = self._transition(job, RunStatus.FAILED)
                failed = failed.model_copy(
                    update={
                        "error": "Travail interrompu par un redemarrage.",
                        "updated_at": utc_now(),
                    }
                )
                recovered.append(self._save(project_id, failed))
        return recovered

    @staticmethod
    def _transition(job: Job, target: RunStatus) -> Job:
        raise_on_invalid_transition(job.status, target)
        return job.model_copy(update={"status": target, "updated_at": utc_now()})

    def _save(self, project_id: UUID, job: Job) -> Job:
        return self.jobs.save(project_id, job)

    @staticmethod
    def _working_directory(project_directory: Path, job_id: UUID) -> Path:
        from app.storage.paths import ensure_internal_directory

        staging = ensure_internal_directory(project_directory, ".staging")
        jobs_staging = ensure_internal_directory(staging, "jobs")
        directory = jobs_staging / str(job_id)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @staticmethod
    def _relative(project_directory: Path, path: Path) -> str:
        return path.relative_to(project_directory).as_posix()
