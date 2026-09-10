import base64
import logging
import mimetypes
import os
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from PIL import Image

from app.domain.models import RunStatus

from .base import (
    Connector,
    ConnectorContext,
    ConnectorKind,
    ConnectorResult,
    ConnectorSubmission,
)

DEFAULT_BASE_URL = "https://api.muapi.ai"
PLACEHOLDER_KEYS = {"", "your_api_key_here", "changeme", "change-me"}
logger = logging.getLogger(__name__)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _api_key() -> str:
    return _env("MU_API_KEY") or _env("MUAPI_API_KEY")


def _has_real_api_key() -> bool:
    return _api_key().lower() not in PLACEHOLDER_KEYS


def _base_url() -> str:
    return _env("MUAPI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _normalize_endpoint(url: str) -> str:
    # MuAPI's catalog currently reports /flux-dev while the live route and docs
    # use /flux-dev-image.
    if url.rstrip("/").endswith("/flux-dev"):
        return f"{url.rstrip('/')}-image"
    return url


def _nested_value(payload: Any, keys: set[str]) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and value:
                return value
        for value in payload.values():
            found = _nested_value(value, keys)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _nested_value(item, keys)
            if found:
                return found
    return None


def _extract_image_url(payload: Any) -> str | None:
    outputs = _nested_value(payload, {"outputs"})
    if isinstance(outputs, list):
        for item in outputs:
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                return item
    value = _nested_value(
        payload,
        {"image_url", "imageUrl", "output_url", "outputUrl", "signed_url"},
    )
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                return item
    return None


def _extract_poll_url(payload: Any) -> str | None:
    urls = _nested_value(payload, {"urls"})
    if isinstance(urls, dict):
        value = urls.get("get") or urls.get("result")
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return None


def _extract_run_id(payload: Any) -> str | None:
    value = _nested_value(
        payload,
        {
            "request_id",
            "requestId",
            "prediction_id",
            "predictionId",
            "run_id",
            "runId",
            "task_id",
            "taskId",
            "id",
        },
    )
    return str(value) if value else None


def _submission_summary(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"type": type(payload).__name__}
    data = payload.get("data")
    urls = data.get("urls") if isinstance(data, dict) else None
    outputs = data.get("outputs") if isinstance(data, dict) else None
    return {
        "top_keys": sorted(payload.keys()),
        "data_keys": sorted(data.keys()) if isinstance(data, dict) else None,
        "data_id": data.get("id") if isinstance(data, dict) else None,
        "data_status": data.get("status") if isinstance(data, dict) else None,
        "data_model": data.get("model") if isinstance(data, dict) else None,
        "data_error": data.get("error") if isinstance(data, dict) else None,
        "data_urls_keys": sorted(urls.keys()) if isinstance(urls, dict) else None,
        "data_output_count": len(outputs) if isinstance(outputs, list) else None,
        "request_id": payload.get("request_id") or payload.get("requestId"),
        "prediction_id": payload.get("prediction_id") or payload.get("predictionId"),
        "task_id": payload.get("task_id") or payload.get("taskId"),
        "run_id": payload.get("run_id") or payload.get("runId"),
        "status": payload.get("status"),
    }


def _status_is_terminal(payload: Any) -> bool:
    value = _nested_value(payload, {"status", "state"})
    terminal_statuses = {"completed", "complete", "succeeded", "success", "failed"}
    return str(value).lower() in terminal_statuses


def _status_is_failed(payload: Any) -> bool:
    value = _nested_value(payload, {"status", "state"})
    return str(value).lower() in {"failed", "error", "cancelled", "canceled"}


class MuApiConnector(Connector):
    endpoint_env: str
    workflow_env: str
    model_env: str
    default_model: str

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "provider": "muapi",
            "kind": self.kind.value,
            "configured": self.configured,
            "secret_present": _has_real_api_key(),
            "workflow_id_present": bool(_env(self.workflow_env)),
            "direct_endpoint_present": bool(_env(self.endpoint_env)),
        }

    @property
    def configured(self) -> bool:
        return _has_real_api_key() and bool(self.endpoint_url)

    @property
    def endpoint_url(self) -> str:
        direct = _env(self.endpoint_env)
        if direct:
            return _normalize_endpoint(direct)
        workflow_id = _env(self.workflow_env)
        if workflow_id:
            return f"{_base_url()}/workflow/{workflow_id}/api-execute"
        return ""

    def check(self) -> dict[str, Any]:
        return {
            "available": self.configured,
            "secret_present": _has_real_api_key(),
            "configured": self.configured,
            "message": (
                "Connecteur MuAPI configure."
                if self.configured
                else "Configurez MU_API_KEY et un endpoint ou workflow MuAPI."
            ),
        }

    def submit(
        self,
        parameters: dict,
        context: ConnectorContext,
    ) -> ConnectorSubmission:
        self.validate(parameters)
        if not self.configured:
            raise ValueError("Connecteur MuAPI non configure.")
        payload = self._payload(parameters, context)
        logger.info(
            "muapi submit connector=%s node=%s run=%s endpoint=%s payload_keys=%s",
            self.id,
            context.node_id,
            context.run_id,
            self.endpoint_url,
            sorted(payload.keys()),
        )
        response_payload = self._post_json(self.endpoint_url, payload)
        image_url = _extract_image_url(response_payload)
        run_id = _extract_run_id(response_payload) or uuid4().hex
        logger.info(
            "muapi submitted connector=%s remote_id=%s "
            "has_image_url=%s has_poll_url=%s response_summary=%s",
            self.id,
            run_id,
            image_url is not None,
            _extract_poll_url(response_payload) is not None,
            _submission_summary(response_payload),
        )
        if image_url is None:
            image_url = self._poll_for_image_url(
                run_id,
                _extract_poll_url(response_payload) or self._default_poll_url(run_id),
            )
        output_path = context.working_directory / f"{uuid4().hex}.png"
        self._download(image_url, output_path)
        logger.info(
            "muapi completed connector=%s remote_id=%s output=%s",
            self.id,
            run_id,
            output_path,
        )
        return ConnectorSubmission(
            external_id=run_id,
            status=RunStatus.COMPLETED,
            output_path=output_path,
        )

    def fetch_results(self, submission: ConnectorSubmission) -> ConnectorResult:
        path = submission.output_path
        with Image.open(path) as image:
            width, height = image.size
        return ConnectorResult(
            output_path=path,
            media_type="image/png",
            width=width,
            height=height,
        )

    def normalize_error(self, error: Exception) -> str:
        message = super().normalize_error(error)
        api_key = _api_key()
        if api_key:
            message = message.replace(api_key, "[REDACTED]")
        return message

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=float(_env("MUAPI_TIMEOUT_SECONDS", "60"))) as client:
            response = client.post(url, json=payload, headers=self._headers())
            self._log_http_error(response, "POST", url)
            response.raise_for_status()
            return response.json()

    def _get_json(self, url: str) -> dict[str, Any]:
        with httpx.Client(timeout=float(_env("MUAPI_TIMEOUT_SECONDS", "60"))) as client:
            response = client.get(url, headers=self._headers())
            self._log_http_error(response, "GET", url)
            response.raise_for_status()
            return response.json()

    def _download(self, url: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=float(_env("MUAPI_TIMEOUT_SECONDS", "60"))) as client:
            response = client.get(url, headers=self._headers(include_json=False))
            self._log_http_error(response, "GET", url)
            response.raise_for_status()
            output_path.write_bytes(response.content)

    def _poll_for_image_url(self, run_id: str, poll_url: str | None = None) -> str:
        max_wait = float(_env("MUAPI_MAX_WAIT_SECONDS", "180"))
        interval = float(_env("MUAPI_POLL_INTERVAL_SECONDS", "2"))
        deadline = time.monotonic() + max_wait
        status_url = f"{_base_url()}/workflow/run/{run_id}/status"
        outputs_url = f"{_base_url()}/workflow/run/{run_id}/api-outputs"
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            try:
                status_payload = self._get_json(poll_url or status_url)
            except httpx.HTTPStatusError as error:
                if poll_url is not None and error.response.status_code == 404:
                    logger.info(
                        "muapi poll pending connector=%s remote_id=%s "
                        "attempt=%s status=404",
                        self.id,
                        run_id,
                        attempt,
                    )
                    time.sleep(interval)
                    continue
                raise
            status_value = _nested_value(status_payload, {"status", "state"})
            logger.info(
                "muapi poll connector=%s remote_id=%s attempt=%s status=%s",
                self.id,
                run_id,
                attempt,
                status_value,
            )
            if _status_is_failed(status_payload):
                raise RuntimeError(f"MuAPI run {run_id} a echoue.")
            image_url = _extract_image_url(status_payload)
            if image_url:
                return image_url
            if _status_is_terminal(status_payload):
                if poll_url is not None:
                    raise RuntimeError("MuAPI n'a retourne aucune URL d'image.")
                outputs_payload = self._get_json(outputs_url)
                image_url = _extract_image_url(outputs_payload)
                if image_url:
                    return image_url
                raise RuntimeError("MuAPI n'a retourne aucune URL d'image.")
            time.sleep(interval)
        raise TimeoutError("MuAPI n'a pas termine avant le delai configure.")

    def _default_poll_url(self, run_id: str) -> str | None:
        if "/api/v1/" in self.endpoint_url and "/workflow/" not in self.endpoint_url:
            return f"{_base_url()}/api/v1/predictions/{run_id}/result"
        return None

    def _log_http_error(self, response: httpx.Response, method: str, url: str) -> None:
        if response.status_code < 400:
            return
        logger.warning(
            "muapi http error connector=%s method=%s url=%s status=%s body=%s",
            self.id,
            method,
            url,
            response.status_code,
            self.normalize_error(response.text[:1000]),
        )

    @staticmethod
    def _headers(*, include_json: bool = True) -> dict[str, str]:
        headers = {"x-api-key": _api_key()}
        if include_json:
            headers["Content-Type"] = "application/json"
        return headers

    def _model(self) -> str:
        return _env(self.model_env, self.default_model)

    def _payload(self, parameters: dict, context: ConnectorContext) -> dict[str, Any]:
        raise NotImplementedError


class MuApiGenerationConnector(MuApiConnector):
    id = "muapi-generation"
    kind = ConnectorKind.GENERATION
    endpoint_env = "MUAPI_GENERATION_URL"
    workflow_env = "MUAPI_GENERATION_WORKFLOW_ID"
    model_env = "MUAPI_GENERATION_MODEL"
    default_model = ""

    def validate(self, parameters: dict) -> None:
        width = parameters.get("width", 1024)
        height = parameters.get("height", 1024)
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("width and height must be integers")
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")

    def _payload(self, parameters: dict, context: ConnectorContext) -> dict[str, Any]:
        payload = {
            "prompt": context.inputs.get("prompt", ""),
            "image": parameters.get("image", ""),
            "size": f"{parameters.get('width', 1024)}*{parameters.get('height', 1024)}",
            "num_images": parameters.get("num_images", 1),
            "num_inference_steps": parameters.get("num_inference_steps", 28),
            "guidance_scale": parameters.get("guidance_scale", 3.5),
            "enable_base64_output": False,
            "enable_safety_checker": parameters.get("enable_safety_checker", True),
        }
        payload["seed"] = parameters.get("seed", -1)
        if self._model():
            payload["model"] = self._model()
        return payload


class MuApiUpscaleConnector(MuApiConnector):
    id = "muapi-upscale"
    kind = ConnectorKind.UPSCALE
    endpoint_env = "MUAPI_UPSCALE_URL"
    workflow_env = "MUAPI_UPSCALE_WORKFLOW_ID"
    model_env = "MUAPI_UPSCALE_MODEL"
    default_model = ""

    def validate(self, parameters: dict) -> None:
        scale = parameters.get("scale", 2)
        if not isinstance(scale, int) or scale <= 0:
            raise ValueError("scale must be a positive integer")

    def _payload(self, parameters: dict, context: ConnectorContext) -> dict[str, Any]:
        image = context.inputs.get("image")
        if not image:
            raise ValueError("upscale requires an input image")
        image_path = Path(image)
        if not image_path.is_file():
            raise ValueError("upscale input image is missing")
        payload = {
            "image_base64": base64.b64encode(image_path.read_bytes()).decode("ascii"),
            "image_media_type": mimetypes.guess_type(image_path.name)[0]
            or "image/png",
            "scale": parameters.get("scale", 2),
        }
        if self._model():
            payload["model"] = self._model()
        return payload
