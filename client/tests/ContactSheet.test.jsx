import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ContactSheet from "../components/gallery/ContactSheet";
import { getGallery } from "../lib/api/gallery";

vi.mock("../lib/api/gallery", () => ({
  getGallery: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ContactSheet", () => {
  it("renders selected thumbnails and placeholder cards", async () => {
    getGallery.mockResolvedValue([
      {
        character_id: "with-selection",
        character_name: "Auguste",
        character_slug: "auguste",
        selected_asset: {
          id: "asset-uuid",
          kind: "generation",
          thumbnail_relative_path: "thumbnails/asset-uuid.png",
        },
      },
      {
        character_id: "without-selection",
        character_name: "Ecuyere",
        character_slug: "ecuyere",
        selected_asset: null,
      },
    ]);

    render(<ContactSheet projectId="project-uuid" />);

    expect(await screen.findByText("Auguste")).toBeInTheDocument();
    expect(screen.getByText("Ecuyere")).toBeInTheDocument();
    expect(screen.getByText("Aucune selection")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Auguste/ })).toHaveAttribute(
      "href",
      "/projects/project-uuid/characters/with-selection",
    );
  });
});
