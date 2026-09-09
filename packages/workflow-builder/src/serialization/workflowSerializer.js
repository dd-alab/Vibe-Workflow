import { nodeDefinitionMap } from "../registry/nodeDefinitions";

export function workflowToFlow(workflow, definitions) {
  const map = nodeDefinitionMap(definitions);
  const nodes = (workflow?.nodes || []).map((node) => {
    const definition = map[node.type] || {};
    return {
      id: node.id,
      type: node.type,
      position: node.position || { x: 0, y: 0 },
      data: {
        definition,
        parameters: node.parameters || {},
        connectorId: node.connector_id ?? null,
      },
    };
  });
  const edges = (workflow?.edges || []).map((edge) => ({
    id: edge.id,
    source: edge.source_node_id,
    sourceHandle: edge.source_port,
    target: edge.target_node_id,
    targetHandle: edge.target_port,
  }));
  return { nodes, edges };
}

export function flowToWorkflow(nodes, edges, previousWorkflow = {}) {
  return {
    schema_version: 1,
    id: previousWorkflow?.id ?? null,
    project_id: previousWorkflow?.project_id ?? null,
    name: previousWorkflow?.name ?? "Sans titre",
    nodes: (nodes || []).map((node) => ({
      id: node.id,
      type: node.type,
      version: 1,
      position: node.position || { x: 0, y: 0 },
      connector_id: node.data?.connectorId ?? null,
      parameters: node.data?.parameters || {},
    })),
    edges: (edges || []).map((edge) => ({
      id: edge.id,
      source_node_id: edge.source,
      source_port: edge.sourceHandle,
      target_node_id: edge.target,
      target_port: edge.targetHandle,
    })),
  };
}

export function generateNodeId(nodeType, existingIds) {
  const prefix = nodeType.replace(/_/g, "-");
  let index = 1;
  while (existingIds.has(`${prefix}-${index}`)) {
    index += 1;
  }
  return `${prefix}-${index}`;
}

export function generateEdgeId(source, target, existingIds) {
  let id = `${source}-${target}`;
  let index = 1;
  while (existingIds.has(id)) {
    id = `${source}-${target}-${index}`;
    index += 1;
  }
  return id;
}
