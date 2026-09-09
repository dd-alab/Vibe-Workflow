from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .validation import ensure_no_secrets

PORT_CHARACTER = "character"
PORT_PROMPT = "prompt"
PORT_IMAGE = "image"


class NodePort(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=120)
    required: bool = True


class NodeParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=120)
    default: Any = None
    required: bool = False


class NodeDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    description: str = ""
    inputs: list[NodePort] = Field(default_factory=list)
    outputs: list[NodePort] = Field(default_factory=list)
    parameters: list[NodeParameter] = Field(default_factory=list)
    connector_required: bool = False

    @property
    def input_ports(self) -> dict[str, NodePort]:
        return {port.name: port for port in self.inputs}

    @property
    def output_ports(self) -> dict[str, NodePort]:
        return {port.name: port for port in self.outputs}


NODE_DEFINITIONS: list[NodeDefinition] = [
    NodeDefinition(
        type="character_input",
        name="Entree personnage",
        category="entree",
        description="Charge les textes, prompts et references du personnage.",
        inputs=[],
        outputs=[NodePort(name="character", type=PORT_CHARACTER)],
        parameters=[],
        connector_required=False,
    ),
    NodeDefinition(
        type="prompt_variant",
        name="Variante de prompt",
        category="prompt",
        description="Selectionne ou combine un prompt libre avec des blocs optionnels.",
        inputs=[NodePort(name="character", type=PORT_CHARACTER)],
        outputs=[NodePort(name="prompt", type=PORT_PROMPT)],
        parameters=[
            NodeParameter(name="prompt_text", type="string", default="", required=True),
        ],
        connector_required=False,
    ),
    NodeDefinition(
        type="image_generation",
        name="Generation image",
        category="generation",
        description="Appelle un connecteur configurable de generation.",
        inputs=[NodePort(name="prompt", type=PORT_PROMPT)],
        outputs=[NodePort(name="image", type=PORT_IMAGE)],
        parameters=[
            NodeParameter(name="width", type="integer", default=1024),
            NodeParameter(name="height", type="integer", default=1024),
            NodeParameter(name="seed", type="integer", default=None),
        ],
        connector_required=True,
    ),
    NodeDefinition(
        type="result_set",
        name="Lot de resultats",
        category="sortie",
        description="Enregistre les images brutes dans le dossier generations.",
        inputs=[NodePort(name="image", type=PORT_IMAGE)],
        outputs=[],
        parameters=[
            NodeParameter(name="prefix", type="string", default="generation"),
        ],
        connector_required=False,
    ),
    NodeDefinition(
        type="selection",
        name="Selection",
        category="tri",
        description="Marque favoris, rejets et image courante.",
        inputs=[NodePort(name="image", type=PORT_IMAGE)],
        outputs=[NodePort(name="image", type=PORT_IMAGE)],
        parameters=[
            NodeParameter(
                name="classification",
                type="string",
                default="neutral",
            ),
        ],
        connector_required=False,
    ),
    NodeDefinition(
        type="upscale",
        name="Upscale",
        category="sortie",
        description="Appelle un connecteur d'upscale depuis une image selectionnee.",
        inputs=[NodePort(name="image", type=PORT_IMAGE)],
        outputs=[NodePort(name="image", type=PORT_IMAGE)],
        parameters=[
            NodeParameter(name="scale", type="integer", default=2),
        ],
        connector_required=True,
    ),
    NodeDefinition(
        type="export",
        name="Export",
        category="sortie",
        description="Copie ou convertit la version finale dans le dossier exports.",
        inputs=[NodePort(name="image", type=PORT_IMAGE)],
        outputs=[],
        parameters=[
            NodeParameter(name="filename", type="string", default=""),
            NodeParameter(name="format", type="string", default="png"),
        ],
        connector_required=False,
    ),
]

NODE_DEFINITION_BY_TYPE: dict[str, NodeDefinition] = {
    definition.type: definition for definition in NODE_DEFINITIONS
}


def node_definitions_payload() -> list[dict[str, Any]]:
    return [
        ensure_no_secrets(definition.model_dump(mode="json"))
        for definition in NODE_DEFINITIONS
    ]
