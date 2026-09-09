import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import WorkflowEditorClient from "../components/workflows/WorkflowEditorClient";
import { listCharacters } from "../lib/api/characters";
import {
  createWorkflowRun,
  getJob,
  getWorkflowRun,
} from "../lib/api/jobs";
import {
  getWorkflow,
  getWorkflowNodeDefinitions,
  updateWorkflow,
} from "../lib/api/workflows";

vi.mock("workflow-builder", () => ({
  WorkflowBuilder: ({ workflow, onRun }) => (
    <button type="button" onClick={() => onRun(workflow)}>
      Executer workflow
    </button>
  ),
}));

vi.mock("../lib/api/characters", () => ({
  listCharacters: vi.fn(),
}));

vi.mock("../lib/api/jobs", () => ({
  cancelJob: vi.fn(),
  createWorkflowRun: vi.fn(),
  getJob: vi.fn(),
  getWorkflowRun: vi.fn(),
  retryJob: vi.fn(),
}));

vi.mock("../lib/api/workflows", () => ({
  createWorkflow: vi.fn(),
  getWorkflow: vi.fn(),
  getWorkflowNodeDefinitions: vi.fn(),
  updateWorkflow: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("WorkflowEditorClient", () => {
  it("saves the workflow and starts a run for the selected character", async () => {
    const workflow = {
      id: "workflow-uuid",
      name: "Generation",
      nodes: [],
      edges: [],
    };
    const run = {
      id: "run-uuid",
      status: "completed",
      job_ids: ["job-uuid"],
      updated_at: "2026-09-09T10:00:00Z",
    };
    getWorkflow.mockResolvedValue(workflow);
    getWorkflowNodeDefinitions.mockResolvedValue([]);
    listCharacters.mockResolvedValue([
      { id: "character-uuid", name: "Auguste" },
    ]);
    updateWorkflow.mockResolvedValue(workflow);
    createWorkflowRun.mockResolvedValue(run);
    getWorkflowRun.mockResolvedValue(run);
    getJob.mockResolvedValue({
      id: "job-uuid",
      status: "completed",
      node_id: "generate",
      connector_id: "mock-generation",
    });

    render(
      <WorkflowEditorClient
        projectId="project-uuid"
        workflowId="workflow-uuid"
      />,
    );

    await screen.findByText("Executer workflow");
    fireEvent.click(screen.getByText("Executer workflow"));

    await waitFor(() => {
      expect(updateWorkflow).toHaveBeenCalledWith(
        "project-uuid",
        "workflow-uuid",
        workflow,
      );
      expect(createWorkflowRun).toHaveBeenCalledWith("project-uuid", {
        workflow_id: "workflow-uuid",
        character_id: "character-uuid",
      });
      expect(screen.getByText("mock-generation")).toBeInTheDocument();
    });
  });
});
