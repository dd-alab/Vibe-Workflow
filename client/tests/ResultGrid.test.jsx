import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ResultGrid from "../components/characters/ResultGrid";
import { exportAsset, selectAsset, updateAsset } from "../lib/api/assets";

vi.mock("../lib/api/assets", async () => {
  const actual = await vi.importActual("../lib/api/assets");
  return {
    ...actual,
    exportAsset: vi.fn(),
    selectAsset: vi.fn(),
    updateAsset: vi.fn(),
  };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ResultGrid", () => {
  it("classifies, selects and exports result assets", async () => {
    const character = {
      id: "character-uuid",
      name: "Auguste",
      revision: 4,
      selected_asset_id: null,
      assets: [
        {
          id: "asset-uuid",
          kind: "generation",
          classification: "neutral",
          thumbnail_relative_path: "thumbnails/asset-uuid.png",
        },
      ],
    };
    const onCharacterChange = vi.fn();
    const onBusyChange = vi.fn();
    updateAsset.mockResolvedValue({ ...character, revision: 5 });
    selectAsset.mockResolvedValue({
      ...character,
      revision: 5,
      selected_asset_id: "asset-uuid",
    });
    exportAsset.mockResolvedValue({ ...character, revision: 5 });

    render(
      <ResultGrid
        projectId="project-uuid"
        character={character}
        disabled={false}
        onCharacterChange={onCharacterChange}
        onBusyChange={onBusyChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Favori" }));
    await waitFor(() => {
      expect(updateAsset).toHaveBeenCalledWith(
        "project-uuid",
        "character-uuid",
        "asset-uuid",
        { expected_revision: 4, classification: "favorite" },
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Selectionner" }));
    await waitFor(() => {
      expect(selectAsset).toHaveBeenCalledWith("project-uuid", "character-uuid", {
        expected_revision: 4,
        asset_id: "asset-uuid",
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Exporter" }));
    await waitFor(() => {
      expect(exportAsset).toHaveBeenCalledWith("project-uuid", "character-uuid", {
        expected_revision: 4,
        asset_id: "asset-uuid",
      });
    });
    expect(onCharacterChange).toHaveBeenCalled();
    expect(onBusyChange).toHaveBeenCalledWith(true);
  });
});
