import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import WorkflowBuilder from "../src/WorkflowBuilder";


vi.mock("../src/components/NodeFlow", () => ({
  default: ({ initialWorkflowData }) => (
    <div data-testid="node-flow">{initialWorkflowData.name}</div>
  ),
}));

describe("WorkflowBuilder", () => {
  it("passes the initial workflow to the canvas", () => {
    render(<WorkflowBuilder initialWorkflowData={{ name: "Portrait flow" }} />);

    expect(screen.getByTestId("node-flow")).toHaveTextContent("Portrait flow");
  });
});
