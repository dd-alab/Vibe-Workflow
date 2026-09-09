from pathlib import Path
from uuid import uuid4

import pytest

from app.connectors.mock_generation import MockGenerationConnector
from app.domain.models import RunStatus
from app.repositories.job_repository import JobRepository
from app.repositories.project_repository import ProjectRepository
from app.services.errors import ServiceValidationError
from app.services.job_runner import JobRunner


def _project(tmp_path):
    return ProjectRepository(tmp_path).create("Circus")


def _project_dir(tmp_path, project) -> Path:
    return tmp_path / project.slug


def test_generation_job_runs_to_completion(tmp_path):
    project = _project(tmp_path)
    runner = JobRunner(JobRepository(tmp_path))

    job = runner.create_job(
        project.id,
        workflow_id=uuid4(),
        run_id=None,
        node_id="generate",
        character_id=None,
        connector_id="mock-generation",
        parameters={"width": 64, "height": 64, "seed": 7},
        inputs={"prompt": "un clown"},
    )

    assert job.status == RunStatus.QUEUED
    result = runner.run_job(project.id, job)
    assert result is not None
    assert result.output_path.is_file()

    loaded = runner.get_job(project.id, job.id)
    assert loaded.status == RunStatus.COMPLETED
    assert len(loaded.output_paths) == 1
    assert (_project_dir(tmp_path, project) / loaded.output_paths[0]).is_file()


def test_upscale_job_copies_input_image(tmp_path):
    project = _project(tmp_path)
    runner = JobRunner(JobRepository(tmp_path))
    source = _project_dir(tmp_path, project) / "source.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image

    Image.new("RGB", (32, 32), (10, 20, 30)).save(source)

    job = runner.create_job(
        project.id,
        workflow_id=uuid4(),
        run_id=None,
        node_id="upscale",
        character_id=None,
        connector_id="mock-upscale",
        parameters={"scale": 2},
        inputs={"image": str(source)},
    )
    runner.run_job(project.id, job)

    loaded = runner.get_job(project.id, job.id)
    assert loaded.status == RunStatus.COMPLETED
    output = _project_dir(tmp_path, project) / loaded.output_paths[0]
    with Image.open(output) as image:
        assert image.size == (64, 64)


def test_cancel_rules(tmp_path):
    project = _project(tmp_path)
    runner = JobRunner(JobRepository(tmp_path))
    job = runner.create_job(
        project.id,
        workflow_id=uuid4(),
        run_id=None,
        node_id="gen",
        character_id=None,
        connector_id="mock-generation",
        parameters={"width": 64, "height": 64},
        inputs={},
    )

    cancelled = runner.cancel_job(project.id, job.id)
    assert cancelled.status == RunStatus.CANCELLED

    completed = runner.create_job(
        project.id,
        workflow_id=uuid4(),
        run_id=None,
        node_id="gen",
        character_id=None,
        connector_id="mock-generation",
        parameters={"width": 64, "height": 64},
        inputs={},
    )
    runner.run_job(project.id, completed)
    with pytest.raises(ServiceValidationError, match="termine"):
        runner.cancel_job(project.id, completed.id)


def test_retry_links_new_attempt_and_succeeds(tmp_path, monkeypatch):
    project = _project(tmp_path)
    runner = JobRunner(JobRepository(tmp_path))
    job = runner.create_job(
        project.id,
        workflow_id=uuid4(),
        run_id=None,
        node_id="gen",
        character_id=None,
        connector_id="mock-generation",
        parameters={"width": 64, "height": 64},
        inputs={"prompt": "un clown"},
    )

    original = MockGenerationConnector.submit

    def failing(self, parameters, context):
        raise RuntimeError("provider down")

    monkeypatch.setattr(MockGenerationConnector, "submit", failing)
    with pytest.raises(RuntimeError, match="provider down"):
        runner.run_job(project.id, job)

    failed = runner.get_job(project.id, job.id)
    assert failed.status == RunStatus.FAILED
    assert failed.error

    monkeypatch.setattr(MockGenerationConnector, "submit", original)
    retried = runner.retry(project.id, job.id)
    assert retried.id != job.id
    assert retried.previous_attempt_id == job.id
    assert retried.status == RunStatus.COMPLETED


def test_recover_interrupted_marks_stuck_jobs_failed(tmp_path):
    project = _project(tmp_path)
    runner = JobRunner(JobRepository(tmp_path))
    job = runner.create_job(
        project.id,
        workflow_id=uuid4(),
        run_id=None,
        node_id="gen",
        character_id=None,
        connector_id="mock-generation",
        parameters={"width": 64, "height": 64},
        inputs={},
    )

    recovered = runner.recover_interrupted(project.id)
    assert len(recovered) == 1
    loaded = runner.get_job(project.id, job.id)
    assert loaded.status == RunStatus.FAILED
    assert "interrompu" in loaded.error.lower()


def test_forbidden_transition_is_rejected(tmp_path):
    project = _project(tmp_path)
    runner = JobRunner(JobRepository(tmp_path))
    job = runner.create_job(
        project.id,
        workflow_id=uuid4(),
        run_id=None,
        node_id="gen",
        character_id=None,
        connector_id="mock-generation",
        parameters={"width": 64, "height": 64},
        inputs={},
    )

    with pytest.raises(ValueError, match="not allowed"):
        runner._transition(job, RunStatus.COMPLETED)
