from uuid import uuid4

import pytest

from app.domain.models import Workflow, WorkflowEdge, WorkflowNode
from app.services.errors import ServiceValidationError
from app.services.workflow_validation import WorkflowValidator


def _node(node_id: str, node_type: str, **kwargs) -> WorkflowNode:
    return WorkflowNode(id=node_id, type=node_type, **kwargs)


def _edge(
    edge_id: str,
    source: str,
    source_port: str,
    target: str,
    target_port: str,
) -> WorkflowEdge:
    return WorkflowEdge(
        id=edge_id,
        source_node_id=source,
        source_port=source_port,
        target_node_id=target,
        target_port=target_port,
    )


def _valid_workflow() -> Workflow:
    return Workflow(
        project_id=uuid4(),
        name="Generation",
        nodes=[
            _node("input", "character_input"),
            _node("prompt", "prompt_variant"),
            _node(
                "generate",
                "image_generation",
                connector_id="mock-generation",
            ),
            _node("results", "result_set"),
        ],
        edges=[
            _edge("e1", "input", "character", "prompt", "character"),
            _edge("e2", "prompt", "prompt", "generate", "prompt"),
            _edge("e3", "generate", "image", "results", "image"),
        ],
    )


def test_valid_workflow_passes_validation() -> None:
    workflow = _valid_workflow()

    assert WorkflowValidator().validate(workflow) is workflow


def test_cyclic_graph_is_rejected() -> None:
    workflow = Workflow(
        project_id=uuid4(),
        name="Cycle",
        nodes=[
            _node("selection", "selection"),
            _node("upscale", "upscale", connector_id="mock-upscale"),
        ],
        edges=[
            _edge("e1", "selection", "image", "upscale", "image"),
            _edge("e2", "upscale", "image", "selection", "image"),
        ],
    )

    with pytest.raises(ServiceValidationError, match="cycle"):
        WorkflowValidator().validate(workflow)


def test_incompatible_ports_are_rejected() -> None:
    workflow = _valid_workflow()
    workflow.edges = [
        _edge("e1", "input", "character", "generate", "prompt"),
    ]

    with pytest.raises(ServiceValidationError, match="incompatibles"):
        WorkflowValidator().validate(workflow)


def test_unknown_node_type_is_rejected() -> None:
    workflow = _valid_workflow()
    workflow.nodes[1] = _node("prompt", "unknown-node")

    with pytest.raises(ServiceValidationError, match="inconnu"):
        WorkflowValidator().validate(workflow)


def test_unknown_port_is_rejected() -> None:
    workflow = _valid_workflow()
    workflow.edges = [
        _edge("e1", "input", "unknown", "prompt", "character"),
    ]

    with pytest.raises(ServiceValidationError, match="port de sortie"):
        WorkflowValidator().validate(workflow)


def test_self_loop_is_rejected() -> None:
    workflow = _valid_workflow()
    workflow.edges = [
        _edge("e1", "input", "character", "input", "character"),
    ]

    with pytest.raises(ServiceValidationError, match="lui-meme"):
        WorkflowValidator().validate(workflow)


def test_duplicate_node_ids_are_rejected() -> None:
    workflow = _valid_workflow()
    workflow.nodes.append(_node("input", "prompt_variant"))

    with pytest.raises(ServiceValidationError, match="meme identifiant"):
        WorkflowValidator().validate(workflow)


def test_duplicate_edge_ids_are_rejected() -> None:
    workflow = _valid_workflow()
    workflow.edges.append(_edge("e3", "prompt", "prompt", "generate", "prompt"))

    with pytest.raises(ServiceValidationError, match="meme identifiant"):
        WorkflowValidator().validate(workflow)


def test_missing_required_connector_is_rejected() -> None:
    workflow = _valid_workflow()
    workflow.nodes[2] = _node("generate", "image_generation")

    with pytest.raises(ServiceValidationError, match="connecteur"):
        WorkflowValidator().validate(workflow)


def test_forbidden_connector_is_rejected() -> None:
    workflow = _valid_workflow()
    workflow.nodes[0] = _node(
        "input", "character_input", connector_id="mock-generation"
    )

    with pytest.raises(ServiceValidationError, match="connecteur"):
        WorkflowValidator().validate(workflow)


def test_secret_like_parameter_is_rejected_at_model_level() -> None:
    with pytest.raises(Exception, match="secret"):
        _node(
            "generate",
            "image_generation",
            parameters={"api_key": "sentinel-secret"},
        )
