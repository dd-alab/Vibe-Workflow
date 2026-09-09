import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ProjectsView from "../components/projects/ProjectsView";
import { createProject, listProjects } from "../lib/api/projects";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("../lib/api/projects", () => ({
  createProject: vi.fn(),
  listProjects: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ProjectsView", () => {
  it("shows loading then the empty state", async () => {
    let resolveProjects;
    listProjects.mockReturnValue(
      new Promise((resolve) => {
        resolveProjects = resolve;
      }),
    );

    render(<ProjectsView />);
    expect(screen.getByText("Chargement des projets...")).toBeInTheDocument();

    resolveProjects([]);
    expect(
      await screen.findByText("Aucun projet pour le moment"),
    ).toBeInTheDocument();
  });

  it("keeps API errors visible and offers a retry", async () => {
    listProjects
      .mockRejectedValueOnce(new Error("Backend local inaccessible"))
      .mockResolvedValueOnce([]);

    render(<ProjectsView />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Backend local inaccessible",
    );
    fireEvent.click(screen.getByRole("button", { name: "Reessayer" }));
    expect(
      await screen.findByText("Aucun projet pour le moment"),
    ).toBeInTheDocument();
  });

  it("creates a trimmed project and opens it by UUID", async () => {
    listProjects.mockResolvedValue([]);
    createProject.mockResolvedValue({ id: "project-uuid" });
    render(<ProjectsView />);
    await screen.findByText("Aucun projet pour le moment");

    fireEvent.change(screen.getByLabelText("Nom du projet"), {
      target: { value: "  Portraits du cirque  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Creer le projet" }));

    await waitFor(() => {
      expect(createProject).toHaveBeenCalledWith({
        name: "Portraits du cirque",
      });
      expect(push).toHaveBeenCalledWith("/projects/project-uuid");
    });
  });
});
