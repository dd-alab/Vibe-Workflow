export const PORT_CHARACTER = "character";
export const PORT_PROMPT = "prompt";
export const PORT_IMAGE = "image";
export const PORT_ARRAY = "array";

export const defaultNodeDefinitions = [
  {
    type: "character_input",
    name: "Entree asset",
    category: "entree",
    description: "Charge les textes, prompts et references de l'asset.",
    inputs: [],
    outputs: [{ name: "character", type: PORT_CHARACTER }],
    parameters: [],
    connectorRequired: false,
  },
  {
    type: "prompt_variant",
    name: "Variante de prompt",
    category: "prompt",
    description: "Selectionne ou combine un prompt libre avec des blocs optionnels.",
    inputs: [{ name: "character", type: PORT_CHARACTER }],
    outputs: [{ name: "prompt", type: PORT_PROMPT }],
    parameters: [
      { name: "prompt_text", type: "string", default: "", required: true },
    ],
    connectorRequired: false,
  },
  {
    type: "prompt_concatenator",
    name: "Prompt Concatenator",
    category: "prompt",
    description: "Connect multiple prompts to one output prompt.",
    inputs: [
      { name: "prompt_1", type: PORT_PROMPT, required: false },
      { name: "prompt_2", type: PORT_PROMPT, required: false },
    ],
    outputs: [{ name: "prompt", type: PORT_PROMPT }],
    parameters: [
      { name: "additional_text", type: "string", default: "" },
      { name: "input_count", type: "integer", default: 2, hidden: true },
    ],
    connectorRequired: false,
  },
  {
    type: "text_iterator",
    name: "Text Iterator",
    category: "prompt",
    description: "Iterate over a list of text values.",
    inputs: [{ name: "array", type: PORT_ARRAY, required: false }],
    outputs: [{ name: "text", type: PORT_PROMPT }],
    parameters: [{ name: "items", type: "text_list", default: [""] }],
    connectorRequired: false,
  },
  {
    type: "image_generation",
    name: "Generation image",
    category: "generation",
    description: "Appelle un connecteur configurable de generation.",
    inputs: [{ name: "prompt", type: PORT_PROMPT }],
    outputs: [{ name: "image", type: PORT_IMAGE }],
    parameters: [
      { name: "width", type: "integer", default: 1024 },
      { name: "height", type: "integer", default: 1024 },
      { name: "seed", type: "integer", default: null },
    ],
    connectorRequired: true,
  },
  {
    type: "result_set",
    name: "Lot de resultats",
    category: "sortie",
    description: "Enregistre les images brutes dans le dossier generations.",
    inputs: [{ name: "image", type: PORT_IMAGE }],
    outputs: [],
    parameters: [{ name: "prefix", type: "string", default: "generation" }],
    connectorRequired: false,
  },
  {
    type: "selection",
    name: "Selection",
    category: "tri",
    description: "Marque favoris, rejets et image courante.",
    inputs: [{ name: "image", type: PORT_IMAGE }],
    outputs: [{ name: "image", type: PORT_IMAGE }],
    parameters: [
      { name: "classification", type: "string", default: "neutral" },
    ],
    connectorRequired: false,
  },
  {
    type: "upscale",
    name: "Upscale",
    category: "sortie",
    description: "Appelle un connecteur d'upscale depuis une image selectionnee.",
    inputs: [{ name: "image", type: PORT_IMAGE }],
    outputs: [{ name: "image", type: PORT_IMAGE }],
    parameters: [{ name: "scale", type: "integer", default: 2 }],
    connectorRequired: true,
  },
  {
    type: "export",
    name: "Export",
    category: "sortie",
    description: "Copie ou convertit la version finale dans le dossier exports.",
    inputs: [{ name: "image", type: PORT_IMAGE }],
    outputs: [],
    parameters: [
      { name: "filename", type: "string", default: "" },
      { name: "format", type: "string", default: "png" },
    ],
    connectorRequired: false,
  },
];

export function connectorRequired(definition) {
  return Boolean(definition?.connectorRequired || definition?.connector_required);
}

export function defaultConnectorId(nodeType) {
  if (nodeType === "image_generation") {
    return "mock-generation";
  }
  if (nodeType === "upscale") {
    return "mock-upscale";
  }
  return null;
}

export function nodeDefinitionMap(definitions) {
  const source = definitions || defaultNodeDefinitions;
  return source.reduce((map, definition) => {
    map[definition.type] = definition;
    return map;
  }, {});
}
