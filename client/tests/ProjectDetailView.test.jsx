import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ProjectDetailView from "../components/projects/ProjectDetailView";
import {
  createCharacter,
  listCharacters,
} from "../lib/api/characters";
import { deleteProject, getProject, updateProject } from "../lib/api/projects";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("../lib/api/projects", () => ({
  deleteProject: vi.fn(),
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
  vi.useRealTimers();
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
    await screen.findByText("Aucun asset dans ce projet");

    fireEvent.change(screen.getByLabelText("Nom de l'asset"), {
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

  it("autosaves free project texts", async () => {
    getProject.mockResolvedValue({
      id: "project-uuid",
      name: "Portraits du cirque",
      revision: 1,
      notes_1: "Note initiale",
      notes_2: "",
    });
    listCharacters.mockResolvedValue([]);
    updateProject.mockResolvedValue({
      id: "project-uuid",
      name: "Portraits du cirque",
      revision: 2,
      notes_1: "Nouvelle note",
      notes_2: "Deuxieme texte",
    });

    render(<ProjectDetailView projectId="project-uuid" />);
    const firstText = await screen.findByRole("textbox", { name: "Texte libre 1" });
    const secondText = screen.getByRole("textbox", { name: "Texte libre 2" });

    vi.useFakeTimers();
    fireEvent.change(firstText, { target: { value: "Nouvelle note" } });
    fireEvent.change(secondText, { target: { value: "Deuxieme texte" } });
    await vi.advanceTimersByTimeAsync(700);
    vi.useRealTimers();

    await waitFor(() => {
      expect(updateProject).toHaveBeenCalledWith("project-uuid", {
        expected_revision: 1,
        notes_1: "Nouvelle note",
        notes_2: "Deuxieme texte",
      });
    });
  });

  it("deletes the project only after double confirmation", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    getProject.mockResolvedValue({
      id: "project-uuid",
      name: "Portraits du cirque",
      revision: 1,
    });
    listCharacters.mockResolvedValue([]);
    deleteProject.mockResolvedValue(null);

    render(<ProjectDetailView projectId="project-uuid" />);
    await screen.findByText("Portraits du cirque");

    fireEvent.click(screen.getByRole("button", { name: "Supprimer le projet" }));

    expect(confirm).toHaveBeenCalledWith(
      "Etes-vous certain de vouloir supprimer ce projet ?",
    );
    const finalDelete = screen.getByRole("button", {
      name: "Supprimer definitivement",
    });
    expect(finalDelete).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Confirmation"), {
      target: { value: "efface ce projet" },
    });
    fireEvent.click(finalDelete);

    await waitFor(() => {
      expect(deleteProject).toHaveBeenCalledWith("project-uuid");
      expect(push).toHaveBeenCalledWith("/projects");
    });
    confirm.mockRestore();
  });
});
