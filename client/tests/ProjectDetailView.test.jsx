import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ProjectDetailView from "../components/projects/ProjectDetailView";
import {
  createCharacter,
  listCharacters,
} from "../lib/api/characters";
import { getProject } from "../lib/api/projects";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("../lib/api/projects", () => ({
  getProject: vi.fn(),
  updateProject: vi.fn(),
}));

vi.mock("../lib/api/characters", () => ({
  createCharacter: vi.fn(),
  listCharacters: vi.fn(),
  updateCharacter: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ProjectDetailView", () => {
  it("lists character names and opens records by UUID", async () => {
    getProject.mockResolvedValue({
      id: "project-uuid",
      name: "Portraits du cirque",
      revision: 1,
    });
    listCharacters.mockResolvedValue([
      {
        id: "character-uuid",
        name: "Auguste melancolique",
        revision: 0,
        updated_at: "2026-09-09T10:00:00Z",
      },
    ]);

    render(<ProjectDetailView projectId="project-uuid" />);

    expect(await screen.findByText("Auguste melancolique")).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "Ouvrir la fiche de Auguste melancolique",
      }),
    ).toHaveAttribute(
      "href",
      "/projects/project-uuid/characters/character-uuid",
    );
  });

  it("creates a character then opens its record", async () => {
    getProject.mockResolvedValue({
      id: "project-uuid",
      name: "Portraits du cirque",
      revision: 1,
    });
    listCharacters.mockResolvedValue([]);
    createCharacter.mockResolvedValue({ id: "new-character-uuid" });
    render(<ProjectDetailView projectId="project-uuid" />);
    await screen.findByText("Aucun personnage dans ce projet");

    fireEvent.change(screen.getByLabelText("Nom du personnage"), {
      target: { value: "  Ecuyere fantome  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Creer et ouvrir" }));

    await waitFor(() => {
      expect(createCharacter).toHaveBeenCalledWith("project-uuid", {
        name: "Ecuyere fantome",
      });
      expect(push).toHaveBeenCalledWith(
        "/projects/project-uuid/characters/new-character-uuid",
      );
    });
  });

  it("moves focus to the selected character rename form", async () => {
    getProject.mockResolvedValue({
      id: "project-uuid",
      name: "Portraits du cirque",
      revision: 1,
    });
    listCharacters.mockResolvedValue([
      {
        id: "character-uuid",
        name: "Auguste melancolique",
        revision: 0,
        updated_at: "2026-09-09T10:00:00Z",
      },
    ]);
    render(<ProjectDetailView projectId="project-uuid" />);
    await screen.findByText("Auguste melancolique");

    fireEvent.click(
      screen.getByRole("button", { name: "Renommer Auguste melancolique" }),
    );

    expect(
      screen.getByRole("textbox", { name: "Renommer Auguste melancolique" }),
    ).toHaveFocus();
  });
});
