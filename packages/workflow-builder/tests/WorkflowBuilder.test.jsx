import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import WorkflowBuilder from "../src/WorkflowBuilder";
import { workflowToFlow, flowToWorkflow } from "../src/serialization/workflowSerializer";
import { canConnect, findCycle, validateWorkflow } from "../src/validation/connectionRules";
import { defaultNodeDefinitions } from "../src/registry/nodeDefinitions";


vi.mock("reactflow", async (importOriginal) => {
  const actual = await importOriginal();
  const MockFlow = ({ children }) => <div data-testid="react-flow">{children}</div>;
  return {
    ...actual,
    __esModule: true,
    default: MockFlow,
    ReactFlow: MockFlow,
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
    ReactFlowProvider: ({ children }) => <div>{children}</div>,
    useReactFlow: () => ({ screenToFlowPosition: (point) => point }),
    applyNodeChanges: (changes, nodes) =>
      changes.reduce((acc, change) => {
        if (change.type === "remove") {
          return acc.filter((node) => node.id !== change.id);
        }
        return acc.map((node) =>
          node.id === change.id ? { ...node, ...change } : node,
        );
      }, nodes),
    applyEdgeChanges: (changes, edges) =>
      changes.reduce((acc, change) => {
        if (change.type === "remove") {
          return acc.filter((edge) => edge.id !== change.id);
        }
        return acc.map((edge) =>
          edge.id === change.id ? { ...edge, ...change } : edge,
        );
      }, edges),
  };
});

describe("WorkflowBuilder", () => {
  it("renders without Next.js context or a server", () => {
    render(
      <WorkflowBuilder
        workflow={{ schema_version: 1, name: "Portrait flow", nodes: [], edges: [] }}
        onChange={() => {}}
      />,
    );

    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Portrait flow")).toBeInTheDocument();
    expect(screen.getByText("Entree personnage")).toBeInTheDocument();
  });

  it("calls onChange when the name is edited", () => {
    const onChange = vi.fn();
    render(
      <WorkflowBuilder
        workflow={{ schema_version: 1, name: "Portrait flow", nodes: [], edges: [] }}
        onChange={onChange}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("Portrait flow"), {
      target: { value: "Portrait de nuit" },
    });

    expect(onChange).toHaveBeenCalled();
  });

  it("adds a node from the local palette", () => {
    const onChange = vi.fn();
    render(
      <WorkflowBuilder
        workflow={{ schema_version: 1, name: "Portrait flow", nodes: [], edges: [] }}
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByText("Entree personnage"));

    const lastWorkflow = onChange.mock.calls.at(-1)[0];
    expect(lastWorkflow.nodes).toHaveLength(1);
    expect(lastWorkflow.nodes[0].type).toBe("character_input");
  });
});

describe("workflowSerializer", () => {
  it("round-trips a workflow without loss", () => {
    const workflow = {
      schema_version: 1,
      id: "wf-1",
      project_id: "proj-1",
      name: "Generation",
      nodes: [
        {
          id: "input",
          type: "character_input",
          version: 1,
          position: { x: 0, y: 0 },
          connector_id: null,
          parameters: {},
        },
        {
          id: "generate",
          type: "image_generation",
          version: 1,
          position: { x: 200, y: 0 },
          connector_id: "mock-generation",
          parameters: { width: 1024 },
        },
      ],
      edges: [
        {
          id: "e1",
          source_node_id: "input",
          source_port: "character",
          target_node_id: "generate",
          target_port: "prompt",
        },
      ],
    };

    const { nodes, edges } = workflowToFlow(workflow, defaultNodeDefinitions);
    const restored = flowToWorkflow(nodes, edges, workflow);

    expect(restored.nodes).toEqual(workflow.nodes);
    expect(restored.edges).toEqual(workflow.edges);
    expect(restored.name).toBe(workflow.name);
  });
});

describe("connectionRules", () => {
  it("allows matching port types", () => {
    expect(
      canConnect(
        { id: "input", type: "character_input" },
        "character",
        { id: "prompt", type: "prompt_variant" },
        "character",
        defaultNodeDefinitions,
      ),
    ).toBe(true);
  });

  it("rejects incompatible port types", () => {
    expect(
      canConnect(
        { id: "input", type: "character_input" },
        "character",
        { id: "generate", type: "image_generation" },
        "prompt",
        defaultNodeDefinitions,
      ),
    ).toBe(false);
  });

  it("rejects self loops", () => {
    expect(
      canConnect(
        { id: "selection", type: "selection" },
        "image",
        { id: "selection", type: "selection" },
        "image",
        defaultNodeDefinitions,
      ),
    ).toBe(false);
  });

  it("detects cycles", () => {
    const nodes = [
      { id: "a", type: "selection" },
      { id: "b", type: "upscale" },
    ];
    const edges = [
      { id: "e1", source: "a", target: "b" },
      { id: "e2", source: "b", target: "a" },
    ];
    expect(findCycle(nodes, edges)).toBe(true);
  });

  it("validates a workflow and returns errors", () => {
    const errors = validateWorkflow(
      [
        { id: "a", type: "unknown_node" },
        { id: "b", type: "selection" },
      ],
      [{ id: "e1", source: "a", sourceHandle: "x", target: "b", targetHandle: "image" }],
      defaultNodeDefinitions,
    );
    expect(errors.length).toBeGreaterThan(0);
  });

  it("accepts a valid serialized workflow", () => {
    const errors = validateWorkflow(
      [
        { id: "input", type: "character_input" },
        { id: "prompt", type: "prompt_variant" },
        { id: "generate", type: "image_generation" },
        { id: "results", type: "result_set" },
      ],
      [
        {
          id: "e1",
          source_node_id: "input",
          source_port: "character",
          target_node_id: "prompt",
          target_port: "character",
        },
        {
          id: "e2",
          source_node_id: "prompt",
          source_port: "prompt",
          target_node_id: "generate",
          target_port: "prompt",
        },
        {
          id: "e3",
          source_node_id: "generate",
          source_port: "image",
          target_node_id: "results",
          target_port: "image",
        },
      ],
      defaultNodeDefinitions,
    );
    expect(errors).toEqual([]);
  });
});
