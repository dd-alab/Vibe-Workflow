from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.domain.models import Job
from app.services.job_runner import JobRunner

from .dependencies import get_job_service

router = APIRouter(tags=["jobs"])
JobServiceDependency = Annotated[JobRunner, Depends(get_job_service)]


@router.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: UUID, service: JobServiceDependency) -> Job:
    return service.get_job_by_id(job_id)


@router.post("/jobs/{job_id}/retry", response_model=Job)
def retry_job(job_id: UUID, service: JobServiceDependency) -> Job:
    return service.retry_by_id(job_id)


@router.post("/jobs/{job_id}/cancel", response_model=Job)
def cancel_job(job_id: UUID, service: JobServiceDependency) -> Job:
    return service.cancel_job_by_id(job_id)
