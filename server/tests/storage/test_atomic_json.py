import json
import os

import pytest

from app.domain.models import WorkflowNode
from app.storage.atomic_json import write_json_atomic


def test_failed_replace_preserves_previous_json(tmp_path, monkeypatch) -> None:
    target = tmp_path / "project.json"
    target.write_text(json.dumps({"version": "previous"}), encoding="utf-8")

    def fail_replace(_source, _target) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        write_json_atomic(target, {"version": "next"})

    assert json.loads(target.read_text(encoding="utf-8")) == {"version": "previous"}
    assert list(tmp_path.glob("*.tmp")) == []


def test_in_place_secret_mutation_is_rejected_on_write(tmp_path) -> None:
    node = WorkflowNode(id="generate", type="image-generation-api")
    node.parameters["accessToken"] = "sentinel-secret"

    with pytest.raises(ValueError, match="secret"):
        write_json_atomic(tmp_path / "workflow.json", node.model_dump(mode="json"))


def test_in_place_secret_mutation_is_rejected_on_direct_serialization() -> None:
    node = WorkflowNode(id="generate", type="image-generation-api")
    node.parameters["clientSecret"] = "sentinel-secret"

    with pytest.raises(ValueError, match="secret"):
        node.model_dump(mode="json")
