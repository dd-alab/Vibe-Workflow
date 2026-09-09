from app.domain.workflow import (
    NODE_DEFINITION_BY_TYPE,
    NODE_DEFINITIONS,
    PORT_CHARACTER,
    PORT_IMAGE,
    PORT_PROMPT,
)


def test_registry_defines_seven_v1_nodes() -> None:
    types = {definition.type for definition in NODE_DEFINITIONS}

    assert types == {
        "character_input",
        "prompt_variant",
        "image_generation",
        "result_set",
        "selection",
        "upscale",
        "export",
    }


def test_registry_ports_and_connector_flags() -> None:
    assert NODE_DEFINITION_BY_TYPE["character_input"].outputs[0].type == PORT_CHARACTER
    assert NODE_DEFINITION_BY_TYPE["prompt_variant"].inputs[0].type == PORT_CHARACTER
    assert NODE_DEFINITION_BY_TYPE["prompt_variant"].outputs[0].type == PORT_PROMPT
    assert NODE_DEFINITION_BY_TYPE["image_generation"].inputs[0].type == PORT_PROMPT
    assert NODE_DEFINITION_BY_TYPE["image_generation"].outputs[0].type == PORT_IMAGE
    assert NODE_DEFINITION_BY_TYPE["result_set"].inputs[0].type == PORT_IMAGE
    assert NODE_DEFINITION_BY_TYPE["selection"].inputs[0].type == PORT_IMAGE
    assert NODE_DEFINITION_BY_TYPE["selection"].outputs[0].type == PORT_IMAGE
    assert NODE_DEFINITION_BY_TYPE["upscale"].inputs[0].type == PORT_IMAGE
    assert NODE_DEFINITION_BY_TYPE["upscale"].outputs[0].type == PORT_IMAGE
    assert NODE_DEFINITION_BY_TYPE["export"].inputs[0].type == PORT_IMAGE

    assert NODE_DEFINITION_BY_TYPE["image_generation"].connector_required
    assert NODE_DEFINITION_BY_TYPE["upscale"].connector_required
    assert not NODE_DEFINITION_BY_TYPE["character_input"].connector_required
    assert not NODE_DEFINITION_BY_TYPE["prompt_variant"].connector_required
    assert not NODE_DEFINITION_BY_TYPE["result_set"].connector_required
    assert not NODE_DEFINITION_BY_TYPE["selection"].connector_required
    assert not NODE_DEFINITION_BY_TYPE["export"].connector_required


def test_node_definitions_payload_is_serializable_without_secrets() -> None:
    payloads = NODE_DEFINITION_BY_TYPE["image_generation"].model_dump(mode="json")

    assert "api_key" not in repr(payloads).lower()
