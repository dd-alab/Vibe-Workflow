import { nodeDefinitionMap } from "../registry/nodeDefinitions";

export function canConnect(
  sourceNode,
  sourceHandle,
  targetNode,
  targetHandle,
  definitions,
) {
  if (!sourceNode || !targetNode || !sourceHandle || !targetHandle) {
    return false;
  }
  const map = nodeDefinitionMap(definitions);
  const sourceDefinition = map[sourceNode.type];
  const targetDefinition = map[targetNode.type];
  if (!sourceDefinition || !targetDefinition) {
    return false;
  }
  const sourcePort = sourceDefinition.outputs.find(
    (port) => port.name === sourceHandle,
  );
  const targetPort = targetDefinition.inputs.find(
    (port) => port.name === targetHandle,
  );
  const dynamicTargetPort =
    targetDefinition.type === "prompt_concatenator" && /^prompt_\d+$/.test(targetHandle)
      ? { name: targetHandle, type: "prompt" }
      : null;
  if (!sourcePort || (!targetPort && !dynamicTargetPort)) {
    return false;
  }
  if (sourceNode.id === targetNode.id) {
    return false;
  }
  return sourcePort.type === (targetPort || dynamicTargetPort).type;
}

function normalizeEdge(edge) {
  return {
    id: edge.id,
    source: edge.source ?? edge.source_node_id,
    sourceHandle: edge.sourceHandle ?? edge.source_port,
    target: edge.target ?? edge.target_node_id,
    targetHandle: edge.targetHandle ?? edge.target_port,
  };
}

export function findCycle(nodes, edges) {
  const ids = new Set(nodes.map((node) => node.id));
  const adjacency = {};
  const inDegree = {};
  nodes.forEach((node) => {
    adjacency[node.id] = new Set();
    inDegree[node.id] = 0;
  });
  edges.forEach((edge) => {
    const normalized = normalizeEdge(edge);
    if (!ids.has(normalized.source) || !ids.has(normalized.target)) {
      return;
    }
    if (!adjacency[normalized.source].has(normalized.target)) {
      adjacency[normalized.source].add(normalized.target);
      inDegree[normalized.target] += 1;
    }
  });

  const queue = Object.keys(inDegree).filter((id) => inDegree[id] === 0);
  let visited = 0;
  while (queue.length > 0) {
    const current = queue.pop();
    visited += 1;
    adjacency[current].forEach((neighbor) => {
      inDegree[neighbor] -= 1;
      if (inDegree[neighbor] === 0) {
        queue.push(neighbor);
      }
    });
  }
  return visited !== Object.keys(inDegree).length;
}

export function validateWorkflow(nodes, edges, definitions) {
  const errors = [];
  const map = nodeDefinitionMap(definitions);
  const seenNodeIds = new Set();
  const seenEdgeIds = new Set();

  nodes.forEach((node) => {
    if (seenNodeIds.has(node.id)) {
      errors.push(`Deux noeuds portent le meme identifiant '${node.id}'.`);
    }
    seenNodeIds.add(node.id);
    if (!map[node.type]) {
      errors.push(`Le type de noeud '${node.type}' est inconnu.`);
    }
  });

  edges.forEach((edge) => {
    const normalized = normalizeEdge(edge);
    if (seenEdgeIds.has(normalized.id)) {
      errors.push(`Deux liaisons portent le meme identifiant '${normalized.id}'.`);
    }
    seenEdgeIds.add(normalized.id);
    if (!canConnect(
      { id: normalized.source, type: nodeTypeOf(normalized.source, nodes) },
      normalized.sourceHandle,
      { id: normalized.target, type: nodeTypeOf(normalized.target, nodes) },
      normalized.targetHandle,
      definitions,
    )) {
      errors.push(`La liaison '${normalized.id}' est invalide ou incompatible.`);
    }
  });

  if (findCycle(nodes, edges)) {
    errors.push("Le workflow contient un cycle.");
  }

  return errors;
}

function nodeTypeOf(id, nodes) {
  const node = nodes.find((item) => item.id === id);
  return node ? node.type : null;
}
