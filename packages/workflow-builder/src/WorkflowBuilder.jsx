"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlowProvider,
  applyNodeChanges,
  applyEdgeChanges,
  useNodesState,
  useEdgesState,
} from "reactflow";
import WorkflowCanvas from "./canvas/WorkflowCanvas";
import {
  connectorRequired,
  defaultNodeDefinitions,
  defaultConnectorId,
  nodeDefinitionMap,
} from "./registry/nodeDefinitions";
import {
  flowToWorkflow,
  generateEdgeId,
  generateNodeId,
  workflowToFlow,
} from "./serialization/workflowSerializer";
import { canConnect, validateWorkflow } from "./validation/connectionRules";

const EMPTY_WORKFLOW = {
  schema_version: 1,
  name: "Sans titre",
  nodes: [],
  edges: [],
};

function nodeTypeOf(id, nodes) {
  const node = nodes.find((item) => item.id === id);
  return node ? node.type : null;
}

export default function WorkflowBuilder({
  workflow,
  nodeDefinitions = defaultNodeDefinitions,
  onChange,
  onSave,
  onRun,
}) {
  const currentWorkflow = workflow || EMPTY_WORKFLOW;
  const [nameDraft, setNameDraft] = useState(currentWorkflow.name);

  const initial = useMemo(
    () => workflowToFlow(currentWorkflow, nodeDefinitions),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const [nodes, setNodes] = useNodesState(initial?.nodes || []);
  const [edges, setEdges] = useEdgesState(initial?.edges || []);

  const lastEmittedRef = useRef(null);

  useEffect(() => {
    if (workflow === lastEmittedRef.current) {
      return;
    }
    const derived = workflowToFlow(workflow, nodeDefinitions);
    setNodes(derived.nodes);
    setEdges(derived.edges);
    setNameDraft(workflow?.name || "Sans titre");
  }, [workflow, nodeDefinitions, setNodes, setEdges]);

  const emit = useCallback(
    (nextNodes, nextEdges, patch = {}) => {
      setNodes(nextNodes);
      setEdges(nextEdges);
      const nextWorkflow = flowToWorkflow(nextNodes, nextEdges, {
        ...currentWorkflow,
        ...patch,
      });
      lastEmittedRef.current = nextWorkflow;
      onChange?.(nextWorkflow);
    },
    [setNodes, setEdges, currentWorkflow, onChange],
  );

  const handleNodesChange = useCallback(
    (changes) => {
      const removedIds = changes
        .filter((change) => change.type === "remove")
        .map((change) => change.id);
      const nextNodes = applyNodeChanges(changes, nodes);
      let nextEdges = edges;
      if (removedIds.length > 0) {
        const removedSet = new Set(removedIds);
        nextEdges = edges.filter(
          (edge) =>
            !removedSet.has(edge.source) && !removedSet.has(edge.target),
        );
      }
      emit(nextNodes, nextEdges);
    },
    [nodes, edges, emit],
  );

  const handleEdgesChange = useCallback(
    (changes) => {
      const nextEdges = applyEdgeChanges(changes, edges);
      emit(nodes, nextEdges);
    },
    [nodes, edges, emit],
  );

  const handleParameterChange = useCallback(
    (nodeId, parameterName, value) => {
      const nextNodes = nodes.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              data: {
                ...node.data,
                parameters: {
                  ...(node.data.parameters || {}),
                  [parameterName]: value,
                },
              },
            }
          : node,
      );
      emit(nextNodes, edges);
    },
    [nodes, edges, emit],
  );

  const handleDeleteNode = useCallback(
    (nodeId) => {
      const nextNodes = nodes.filter((node) => node.id !== nodeId);
      const nextEdges = edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId,
      );
      emit(nextNodes, nextEdges);
    },
    [nodes, edges, emit],
  );

  const handleAddNode = useCallback(
    (type, position) => {
      const existingIds = new Set(nodes.map((node) => node.id));
      const id = generateNodeId(type, existingIds);
      const definition = nodeDefinitionMap(nodeDefinitions)[type];
      const parameters = (definition?.parameters || []).reduce(
        (acc, parameter) => {
          acc[parameter.name] = parameter.default ?? null;
          return acc;
        },
        {},
      );
      const node = {
        id,
        type,
        position: position || {
          x: 80 + nodes.length * 40,
          y: 80,
        },
        data: {
          definition,
          parameters,
          connectorId: connectorRequired(definition)
            ? defaultConnectorId(type)
            : null,
        },
      };
      emit([...nodes, node], edges);
    },
    [nodes, edges, nodeDefinitions, emit],
  );

  const handleConnect = useCallback(
    (connection) => {
      const { source, sourceHandle, target, targetHandle } = connection;
      const valid = canConnect(
        { id: source, type: nodeTypeOf(source, nodes) },
        sourceHandle,
        { id: target, type: nodeTypeOf(target, nodes) },
        targetHandle,
        nodeDefinitions,
      );
      if (!valid) {
        return;
      }
      const existingIds = new Set(edges.map((edge) => edge.id));
      const edge = {
        id: generateEdgeId(source, target, existingIds),
        source,
        sourceHandle,
        target,
        targetHandle,
      };
      emit(nodes, [...edges, edge]);
    },
    [nodes, edges, nodeDefinitions, emit],
  );

  const handleNameChange = useCallback(
    (value) => {
      setNameDraft(value);
      emit(nodes, edges, { name: value });
    },
    [nodes, edges, emit],
  );

  const injectedNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          onChange: (parameterName, value) =>
            handleParameterChange(node.id, parameterName, value),
          onDelete: () => handleDeleteNode(node.id),
        },
      })),
    [nodes, handleParameterChange, handleDeleteNode],
  );

  const errors = useMemo(
    () => validateWorkflow(nodes, edges, nodeDefinitions),
    [nodes, edges, nodeDefinitions],
  );
  const serializedWorkflow = useMemo(
    () => flowToWorkflow(nodes, edges, currentWorkflow),
    [nodes, edges, currentWorkflow],
  );

  return (
    <ReactFlowProvider>
      <div className="flex h-full w-full overflow-hidden bg-[#141310]">
        <div className="flex w-60 shrink-0 flex-col border-r border-white/10 bg-[#181713]">
          <div className="border-b border-white/10 p-4">
            <label className="block text-xs font-medium text-zinc-400">
              Nom du workflow
              <input
                value={nameDraft}
                onChange={(event) => handleNameChange(event.target.value)}
                maxLength={120}
                className="mt-2 min-h-10 w-full rounded-lg border border-white/10 bg-black/40 px-3 text-sm text-zinc-100 outline-none focus:border-accent-focus"
              />
            </label>
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
              Noeuds
            </p>
            <div className="space-y-2">
              {nodeDefinitions.map((definition) => (
                <button
                  key={definition.type}
                  type="button"
                  draggable
                  onDragStart={(event) => {
                    event.dataTransfer.setData(
                      "application/workflow-node",
                      definition.type,
                    );
                    event.dataTransfer.effectAllowed = "move";
                  }}
                  onClick={() => handleAddNode(definition.type)}
                  className="block w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-left text-sm text-zinc-200 hover:border-accent/40 hover:bg-accent/5"
                >
                  <span className="block font-medium">{definition.name}</span>
                  <span className="mt-0.5 block text-xs text-zinc-500">
                    {definition.description}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-white/10 p-3">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => onSave?.(serializedWorkflow)}
                className="min-h-10 flex-1 rounded-lg bg-accent px-3 text-sm font-semibold text-white hover:bg-accent-hover"
              >
                Enregistrer
              </button>
              <button
                type="button"
                onClick={() => onRun?.(serializedWorkflow)}
                className="min-h-10 flex-1 rounded-lg border border-white/10 px-3 text-sm font-medium text-zinc-200 hover:bg-white/5"
              >
                Executer
              </button>
            </div>
          </div>
        </div>

        <div className="relative flex-1">
          <WorkflowCanvas
            nodes={injectedNodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={handleConnect}
            onAddNode={handleAddNode}
          />
          {errors.length > 0 && (
            <div className="absolute bottom-3 left-1/2 max-h-40 w-[90%] max-w-xl -translate-x-1/2 overflow-y-auto rounded-lg border border-red-500/20 bg-red-950/60 p-3 backdrop-blur">
              {errors.map((error) => (
                <p key={error} className="text-xs text-red-200">
                  {error}
                </p>
              ))}
            </div>
          )}
        </div>
      </div>
    </ReactFlowProvider>
  );
}
