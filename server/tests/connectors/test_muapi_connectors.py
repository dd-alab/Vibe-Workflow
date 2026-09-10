import io
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from PIL import Image

from app.connectors.base import ConnectorContext
from app.connectors.muapi import MuApiGenerationConnector, MuApiUpscaleConnector
from app.domain.models import RunStatus


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (16, 12), (97, 92, 80)).save(output, format="PNG")
    return output.getvalue()


class FakeClient:
    requests: list[tuple[str, str, dict | None]] = []

    def __init__(self, *, timeout):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def post(self, url, *, json, headers):
        self.requests.append(("POST", url, json))
        assert headers["x-api-key"] == "sentinel-muapi-key"
        return httpx.Response(
            200,
            json={"data": {"id": "remote-run", "outputs": ["https://cdn.local/result.png"]}},
            request=httpx.Request("POST", url),
        )

    def get(self, url, *, headers):
        self.requests.append(("GET", url, None))
        assert headers["x-api-key"] == "sentinel-muapi-key"
        return httpx.Response(
            200,
            content=png_bytes(),
            request=httpx.Request("GET", url),
        )


class PollingFakeClient(FakeClient):
    def post(self, url, *, json, headers):
        self.requests.append(("POST", url, json))
        return httpx.Response(
            200,
            json={"run_id": "remote-run"},
            request=httpx.Request("POST", url),
        )

    def get(self, url, *, headers):
        self.requests.append(("GET", url, None))
        if url.endswith("/status"):
            return httpx.Response(
                200,
                json={"status": "completed"},
                request=httpx.Request("GET", url),
            )
        return httpx.Response(
            200,
            json={"outputs": {"image_url": "https://cdn.local/result.png"}},
            request=httpx.Request("GET", url),
        )


class PredictionFakeClient(FakeClient):
    def post(self, url, *, json, headers):
        self.requests.append(("POST", url, json))
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "prediction-123",
                    "status": "processing",
                    "outputs": [],
                    "urls": {
                        "get": "https://api.muapi.ai/api/v1/predictions/prediction-123/result"
                    },
                }
            },
            request=httpx.Request("POST", url),
        )

    def get(self, url, *, headers):
        self.requests.append(("GET", url, None))
        if url.endswith("/result"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "prediction-123",
                        "status": "completed",
                        "outputs": ["https://cdn.local/result.png"],
                    }
                },
                request=httpx.Request("GET", url),
            )
        return httpx.Response(
            200,
            content=png_bytes(),
            request=httpx.Request("GET", url),
        )


class PredictionWithoutUrlFakeClient(PredictionFakeClient):
    def post(self, url, *, json, headers):
        self.requests.append(("POST", url, json))
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "prediction-456",
                    "status": "processing",
                    "outputs": [],
                }
            },
            request=httpx.Request("POST", url),
        )


class PredictionDelayedResultFakeClient(PredictionFakeClient):
    result_attempts = 0

    def post(self, url, *, json, headers):
        self.requests.append(("POST", url, json))
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "prediction-789",
                    "status": "processing",
                    "outputs": [],
                }
            },
            request=httpx.Request("POST", url),
        )

    def get(self, url, *, headers):
        self.requests.append(("GET", url, None))
        if url.endswith("/result"):
            type(self).result_attempts += 1
            if self.result_attempts == 1:
                return httpx.Response(
                    404,
                    json={
                        "detail": {
                            "error": {
                                "code": "REQUEST_NOT_FOUND",
                                "message": "Request ID not found",
                            }
                        }
                    },
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "prediction-789",
                        "status": "completed",
                        "outputs": ["https://cdn.local/result.png"],
                    }
                },
                request=httpx.Request("GET", url),
            )
        return httpx.Response(
            200,
            content=png_bytes(),
            request=httpx.Request("GET", url),
        )


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in (
        "MU_API_KEY",
        "MUAPI_API_KEY",
        "MUAPI_GENERATION_URL",
        "MUAPI_GENERATION_WORKFLOW_ID",
        "MUAPI_UPSCALE_URL",
        "MUAPI_UPSCALE_WORKFLOW_ID",
        "MUAPI_POLL_INTERVAL_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)


def context(tmp_path: Path, inputs: dict | None = None) -> ConnectorContext:
    return ConnectorContext(
        project_id=uuid4(),
        run_id=uuid4(),
        node_id="node",
        character_id=uuid4(),
        working_directory=tmp_path,
        inputs=inputs or {},
    )


def test_muapi_generation_downloads_remote_result(monkeypatch, tmp_path):
    FakeClient.requests = []
    monkeypatch.setenv("MU_API_KEY", "sentinel-muapi-key")
    monkeypatch.setenv("MUAPI_GENERATION_URL", "https://api.local/generate")
    monkeypatch.setattr("app.connectors.muapi.httpx.Client", FakeClient)

    connector = MuApiGenerationConnector()
    submission = connector.submit(
        {"width": 16, "height": 12, "seed": 7},
        context(tmp_path, {"prompt": "un portrait"}),
    )
    result = connector.fetch_results(submission)

    assert submission.status == RunStatus.COMPLETED
    assert result.output_path.is_file()
    assert result.width == 16
    assert FakeClient.requests[0] == (
        "POST",
        "https://api.local/generate",
        {
            "prompt": "un portrait",
            "image": "",
            "size": "16*12",
            "num_images": 1,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "enable_base64_output": False,
            "enable_safety_checker": True,
            "seed": 7,
        },
    )


def test_muapi_generation_can_poll_workflow_api(monkeypatch, tmp_path):
    PollingFakeClient.requests = []
    monkeypatch.setenv("MU_API_KEY", "sentinel-muapi-key")
    monkeypatch.setenv("MUAPI_GENERATION_WORKFLOW_ID", "workflow-123")
    monkeypatch.setenv("MUAPI_POLL_INTERVAL_SECONDS", "0")
    monkeypatch.setattr("app.connectors.muapi.httpx.Client", PollingFakeClient)

    connector = MuApiGenerationConnector()
    submission = connector.submit(
        {"width": 16, "height": 12},
        context(tmp_path, {"prompt": "un portrait"}),
    )

    assert submission.output_path.is_file()
    assert [request[0] for request in PollingFakeClient.requests] == [
        "POST",
        "GET",
        "GET",
        "GET",
    ]


def test_muapi_generation_can_poll_prediction_result_url(monkeypatch, tmp_path):
    PredictionFakeClient.requests = []
    monkeypatch.setenv("MU_API_KEY", "sentinel-muapi-key")
    monkeypatch.setenv("MUAPI_GENERATION_URL", "https://api.muapi.ai/api/v1/flux-dev-image")
    monkeypatch.setenv("MUAPI_POLL_INTERVAL_SECONDS", "0")
    monkeypatch.setattr("app.connectors.muapi.httpx.Client", PredictionFakeClient)

    connector = MuApiGenerationConnector()
    submission = connector.submit(
        {"width": 16, "height": 12},
        context(tmp_path, {"prompt": "un portrait"}),
    )

    assert submission.output_path.is_file()
    assert PredictionFakeClient.requests[1] == (
        "GET",
        "https://api.muapi.ai/api/v1/predictions/prediction-123/result",
        None,
    )


def test_muapi_generation_uses_prediction_poll_fallback(monkeypatch, tmp_path):
    PredictionWithoutUrlFakeClient.requests = []
    monkeypatch.setenv("MU_API_KEY", "sentinel-muapi-key")
    monkeypatch.setenv("MUAPI_GENERATION_URL", "https://api.muapi.ai/api/v1/flux-dev-image")
    monkeypatch.setenv("MUAPI_POLL_INTERVAL_SECONDS", "0")
    monkeypatch.setattr(
        "app.connectors.muapi.httpx.Client", PredictionWithoutUrlFakeClient
    )

    MuApiGenerationConnector().submit(
        {"width": 16, "height": 12},
        context(tmp_path, {"prompt": "un portrait"}),
    )

    assert PredictionWithoutUrlFakeClient.requests[1] == (
        "GET",
        "https://api.muapi.ai/api/v1/predictions/prediction-456/result",
        None,
    )


def test_muapi_generation_retries_pending_prediction_404(monkeypatch, tmp_path):
    PredictionDelayedResultFakeClient.requests = []
    PredictionDelayedResultFakeClient.result_attempts = 0
    monkeypatch.setenv("MU_API_KEY", "sentinel-muapi-key")
    monkeypatch.setenv("MUAPI_GENERATION_URL", "https://api.muapi.ai/api/v1/flux-dev-image")
    monkeypatch.setenv("MUAPI_POLL_INTERVAL_SECONDS", "0")
    monkeypatch.setattr(
        "app.connectors.muapi.httpx.Client", PredictionDelayedResultFakeClient
    )

    submission = MuApiGenerationConnector().submit(
        {"width": 16, "height": 12},
        context(tmp_path, {"prompt": "un portrait"}),
    )

    assert submission.output_path.is_file()
    assert [request[0] for request in PredictionDelayedResultFakeClient.requests] == [
        "POST",
        "GET",
        "GET",
        "GET",
    ]


def test_muapi_generation_normalizes_catalog_flux_dev_endpoint(monkeypatch, tmp_path):
    FakeClient.requests = []
    monkeypatch.setenv("MU_API_KEY", "sentinel-muapi-key")
    monkeypatch.setenv("MUAPI_GENERATION_URL", "https://api.muapi.ai/api/v1/flux-dev")
    monkeypatch.setattr("app.connectors.muapi.httpx.Client", FakeClient)

    MuApiGenerationConnector().submit(
        {"width": 16, "height": 12},
        context(tmp_path, {"prompt": "un portrait"}),
    )

    assert FakeClient.requests[0][1] == "https://api.muapi.ai/api/v1/flux-dev-image"


def test_muapi_upscale_sends_image_content_only_on_submit(monkeypatch, tmp_path):
    FakeClient.requests = []
    source_path = tmp_path / "source.png"
    source_path.write_bytes(png_bytes())
    monkeypatch.setenv("MU_API_KEY", "sentinel-muapi-key")
    monkeypatch.setenv("MUAPI_UPSCALE_URL", "https://api.local/upscale")
    monkeypatch.setattr("app.connectors.muapi.httpx.Client", FakeClient)

    connector = MuApiUpscaleConnector()
    assert "image_base64" not in repr(connector.capabilities)
    connector.submit({"scale": 2}, context(tmp_path, {"image": str(source_path)}))

    payload = FakeClient.requests[0][2]
    assert payload["scale"] == 2
    assert payload["image_media_type"] == "image/png"
    assert payload["image_base64"]
    assert str(source_path) not in repr(payload)


def test_muapi_check_exposes_secret_presence_without_value(monkeypatch):
    monkeypatch.setenv("MU_API_KEY", "sentinel-muapi-key")
    monkeypatch.setenv("MUAPI_GENERATION_URL", "https://api.local/generate")

    status = MuApiGenerationConnector().check()

    assert status["available"] is True
    assert status["secret_present"] is True
    assert "sentinel-muapi-key" not in repr(status)


def test_muapi_errors_redact_api_key(monkeypatch):
    monkeypatch.setenv("MU_API_KEY", "sentinel-muapi-key")

    message = MuApiGenerationConnector().normalize_error(
        RuntimeError("failed with sentinel-muapi-key")
    )

    assert "sentinel-muapi-key" not in message
    assert "[REDACTED]" in message
