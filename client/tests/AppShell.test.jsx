import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AppShell from "../components/AppShell";

vi.mock("next/navigation", () => ({
  useParams: () => ({ projectId: "project-uuid" }),
  usePathname: () => "/projects/project-uuid",
}));

afterEach(cleanup);

describe("AppShell", () => {
  it("links the active project by UUID and disables future sections", () => {
    render(<AppShell>Contenu</AppShell>);

    expect(screen.getByRole("link", { name: "Projet" })).toHaveAttribute(
      "href",
      "/projects/project-uuid",
    );
    expect(screen.getByRole("link", { name: "Projet" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Galerie")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Workflows")).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByText("Connecteurs")).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });
});
