import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AppShell from "../components/AppShell";

vi.mock("next/navigation", () => ({
  useParams: () => ({ projectId: "project-uuid" }),
  usePathname: () => "/projects/project-uuid",
}));

afterEach(cleanup);

describe("AppShell", () => {
  it("links active project sections by UUID and exposes connectors", () => {
    render(<AppShell>Contenu</AppShell>);

    expect(screen.getByRole("link", { name: "Projet" })).toHaveAttribute(
      "href",
      "/projects/project-uuid",
    );
    expect(screen.getByRole("link", { name: "Projet" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Galerie" })).toHaveAttribute(
      "href",
      "/projects/project-uuid/gallery",
    );
    expect(screen.getByRole("link", { name: "Workflows" })).toHaveAttribute(
      "href",
      "/projects/project-uuid/workflows",
    );
    expect(screen.getByRole("link", { name: "Connecteurs" })).toHaveAttribute(
      "href",
      "/connectors",
    );
  });
});
