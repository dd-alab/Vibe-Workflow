import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ConnectorStatus from "../components/connectors/ConnectorStatus";
import { checkConnector, listConnectors } from "../lib/api/connectors";

vi.mock("../lib/api/connectors", () => ({
  checkConnector: vi.fn(),
  listConnectors: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ConnectorStatus", () => {
  it("shows connector readiness without exposing the secret", async () => {
    listConnectors.mockResolvedValue([
      {
        id: "muapi-generation",
        kind: "generation",
        capabilities: { configured: true },
      },
    ]);
    checkConnector.mockResolvedValue({
      id: "muapi-generation",
      kind: "generation",
      available: true,
      secret_present: true,
      message: "Connecteur MuAPI configure.",
    });

    render(<ConnectorStatus />);

    expect(await screen.findByText("muapi-generation")).toBeInTheDocument();
    expect(screen.getByText("Secret: present")).toBeInTheDocument();
    expect(screen.queryByText("sentinel-secret")).not.toBeInTheDocument();
  });
});
