import GenericNode from "./GenericNode";

export const nodeTypes = {
  character_input: GenericNode,
  prompt_variant: GenericNode,
  image_generation: GenericNode,
  result_set: GenericNode,
  selection: GenericNode,
  upscale: GenericNode,
  export: GenericNode,
};

export default GenericNode;
