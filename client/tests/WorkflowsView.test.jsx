import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import WorkflowsView from "../components/workflows/WorkflowsView";
import { getProject } from "../lib/api/projects";
import { listWorkflows } from "../lib/api/workflows";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("../lib/api/projects", () => ({
  getProject: vi.fn(),
}));

vi.mock("../lib/api/workflows", () => ({
  createWorkflow: vi.fn(),
  deleteWorkflow: vi.fn(),
  listWorkflows: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("WorkflowsView", () => {
  it("shows the active project name next to the project return link", async () => {
    getProject.mockResolvedValue({
      id: "project-uuid",
      name: "01 Niepce et la premiere image",
    });
    listWorkflows.mockResolvedValue([]);

    render(<WorkflowsView projectId="project-uuid" />);

    expect(
      await screen.findByText("01 Niepce et la premiere image"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Retour au projet" })).toHaveAttribute(
      "href",
      "/projects/project-uuid",
    );
  });
});
