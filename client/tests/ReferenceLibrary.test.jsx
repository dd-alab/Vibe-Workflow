import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ReferenceLibrary from "../components/characters/ReferenceLibrary";
import {
  deleteReference,
  uploadReference,
} from "../lib/api/assets";

vi.mock("../lib/api/assets", () => ({
  assetContentUrl: (id) => `/api/assets/${id}/content`,
  assetThumbnailUrl: (id) => `/api/assets/${id}/thumbnail`,
  deleteReference: vi.fn(),
  uploadReference: vi.fn(),
}));

const baseCharacter = {
  id: "character-uuid",
  name: "Auguste",
  revision: 0,
  assets: [],
};

function reference(id, overrides = {}) {
  return {
    id,
    kind: "reference",
    media_type: "image/png",
    width: 80,
    height: 60,
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe("ReferenceLibrary", () => {
  it("shows an empty state and an accessible picker", () => {
    render(
      <ReferenceLibrary
        projectId="project-uuid"
        character={baseCharacter}
        disabled={false}
        onCharacterChange={vi.fn()}
        onBusyChange={vi.fn()}
      />,
    );

    expect(screen.getByText("Aucune image de reference")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Choisir des images" })).toBeEnabled();
    expect(screen.getByLabelText("Fichiers de reference")).toHaveAttribute(
      "accept",
      expect.stringContaining("image/png"),
    );
  });

  it("uploads several files sequentially with the newest revision", async () => {
    const firstCharacter = {
      ...baseCharacter,
      revision: 1,
      assets: [reference("asset-1")],
    };
    const secondCharacter = {
      ...baseCharacter,
      revision: 2,
      assets: [reference("asset-1"), reference("asset-2")],
    };
    uploadReference
      .mockResolvedValueOnce(firstCharacter)
      .mockResolvedValueOnce(secondCharacter);
    const onCharacterChange = vi.fn();
    render(
      <ReferenceLibrary
        projectId="project-uuid"
        character={baseCharacter}
        disabled={false}
        onCharacterChange={onCharacterChange}
        onBusyChange={vi.fn()}
      />,
    );
    const files = [
      new File(["one"], "one.png", { type: "image/png" }),
      new File(["two"], "two.webp", { type: "image/webp" }),
    ];

    fireEvent.change(screen.getByLabelText("Fichiers de reference"), {
      target: { files },
    });

    await waitFor(() => expect(uploadReference).toHaveBeenCalledTimes(2));
    expect(uploadReference.mock.calls[0].slice(0, 3)).toEqual([
      "project-uuid",
      "character-uuid",
      files[0],
    ]);
    expect(uploadReference.mock.calls[0][3].expectedRevision).toBe(0);
    expect(uploadReference.mock.calls[1][3].expectedRevision).toBe(1);
    expect(onCharacterChange).toHaveBeenLastCalledWith(secondCharacter);
  });

  it("keeps metadata visible when a thumbnail is missing", () => {
    render(
      <ReferenceLibrary
        projectId="project-uuid"
        character={{
          ...baseCharacter,
          assets: [reference("asset-1")],
        }}
        disabled={false}
        onCharacterChange={vi.fn()}
        onBusyChange={vi.fn()}
      />,
    );

    fireEvent.error(screen.getByAltText("Reference 1 pour Auguste"));

    expect(
      screen.getByText("Fichier ou miniature introuvable"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Supprimer la reference 1" })).toBeEnabled();
  });

  it("deletes only after confirmation and returns the updated character", async () => {
    const character = {
      ...baseCharacter,
      revision: 3,
      assets: [reference("asset-1")],
    };
    const updated = { ...character, revision: 4, assets: [] };
    vi.stubGlobal("confirm", vi.fn(() => true));
    deleteReference.mockResolvedValue(updated);
    const onCharacterChange = vi.fn();
    render(
      <ReferenceLibrary
        projectId="project-uuid"
        character={character}
        disabled={false}
        onCharacterChange={onCharacterChange}
        onBusyChange={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Supprimer la reference 1" }));

    await waitFor(() => {
      expect(deleteReference).toHaveBeenCalledWith(
        "project-uuid",
        "character-uuid",
        "asset-1",
        { expectedRevision: 3 },
      );
      expect(onCharacterChange).toHaveBeenCalledWith(updated);
    });
  });
});
