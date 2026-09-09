import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import CharacterDetailView from "../components/characters/CharacterDetailView";
import {
  createPromptVersion,
  getCharacter,
  updateCharacter,
} from "../lib/api/characters";

vi.mock("../lib/api/characters", () => ({
  activatePromptVersion: vi.fn(),
  createPromptVersion: vi.fn(),
  getCharacter: vi.fn(),
  updateCharacter: vi.fn(),
}));

const character = {
  id: "character-uuid",
  project_id: "project-uuid",
  name: "Auguste melancolique",
  revision: 4,
  short_texts: [
    { id: "text-uuid", text: "Un clown silencieux sous la pluie." },
  ],
  prompt_blocks: [
    { id: "block-uuid", name: "Lumiere", text: "Clair-obscur doux." },
  ],
  prompt_versions: [
    {
      id: "prompt-uuid",
      text: "Portrait serre.",
      block_ids: ["block-uuid"],
      blocks: [{ id: "block-uuid", name: "Lumiere", text: "Clair-obscur doux." }],
      created_at: "2026-09-09T10:00:00Z",
    },
  ],
  active_prompt_version_id: "prompt-uuid",
  assets: [],
  updated_at: "2026-09-09T10:00:00Z",
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CharacterDetailView", () => {
  it("renders saved texts and immutable prompt history", async () => {
    getCharacter.mockResolvedValue(character);
    render(
      <CharacterDetailView
        projectId="project-uuid"
        characterId="character-uuid"
      />,
    );

    expect(await screen.findByDisplayValue(character.short_texts[0].text)).toBeInTheDocument();
    expect(screen.getByText("Portrait serre.")).toBeInTheDocument();
    expect(screen.getByText("Version active")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Portrait serre.")).not.toBeInTheDocument();
    expect(screen.getByText("Lumiere", { selector: "span" })).toBeInTheDocument();
  });

  it("lets reusable blocks referenced by a version stay editable", async () => {
    getCharacter.mockResolvedValue(character);
    render(
      <CharacterDetailView
        projectId="project-uuid"
        characterId="character-uuid"
      />,
    );
    const blockName = await screen.findByDisplayValue("Lumiere");

    expect(blockName).toBeEnabled();
    expect(
      screen.queryByText("Verrouille par les versions de prompt."),
    ).not.toBeInTheDocument();
  });

  it("creates a new prompt with selected reusable blocks", async () => {
    getCharacter.mockResolvedValue(character);
    createPromptVersion.mockResolvedValue({
      ...character,
      revision: 5,
      prompt_versions: [
        ...character.prompt_versions,
        {
          id: "new-prompt-uuid",
          text: "Portrait frontal.",
          block_ids: ["block-uuid"],
          blocks: [{ id: "block-uuid", name: "Lumiere", text: "Clair-obscur doux." }],
          created_at: "2026-09-09T11:00:00Z",
        },
      ],
    });
    render(
      <CharacterDetailView
        projectId="project-uuid"
        characterId="character-uuid"
      />,
    );
    await screen.findByText("Portrait serre.");

    fireEvent.change(screen.getByLabelText("Nouveau prompt"), {
      target: { value: "  Portrait frontal.  " },
    });
    fireEvent.click(screen.getByLabelText("Utiliser le bloc Lumiere"));
    fireEvent.click(screen.getByRole("button", { name: "Creer la version" }));

    await waitFor(() => {
      expect(createPromptVersion).toHaveBeenCalledWith(
        "project-uuid",
        "character-uuid",
        {
          expected_revision: 4,
          text: "Portrait frontal.",
          block_ids: ["block-uuid"],
        },
      );
    });
    expect(await screen.findByText("Portrait frontal.")).toBeInTheDocument();
  });

  it("locks every character editor while a mutation is pending", async () => {
    let resolveUpdate;
    getCharacter.mockResolvedValue(character);
    updateCharacter.mockReturnValue(
      new Promise((resolve) => {
        resolveUpdate = resolve;
      }),
    );
    render(
      <CharacterDetailView
        projectId="project-uuid"
        characterId="character-uuid"
      />,
    );
    const text = await screen.findByDisplayValue(character.short_texts[0].text);

    fireEvent.change(text, { target: { value: "Texte soumis." } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer les textes" }));

    expect(text).toBeDisabled();
    expect(screen.getByLabelText("Nouveau prompt")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Renommer" })).toBeDisabled();

    resolveUpdate({
      ...character,
      revision: 5,
      short_texts: [{ id: "text-uuid", text: "Texte soumis." }],
    });
    expect(await screen.findByDisplayValue("Texte soumis.")).toBeEnabled();
  });
});
