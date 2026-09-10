"use client";

import React, { useCallback, useState } from "react";
import ReactFlow, { useReactFlow } from "reactflow";
import { nodeTypes } from "../nodes";

function ToolButton({ active, label, onClick, children }) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={`grid h-10 w-10 place-items-center rounded-full text-zinc-200 transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus ${
        active ? "bg-white text-zinc-950 hover:bg-white" : ""
      }`}
    >
      {children}
    </button>
  );
}

function LockIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="6" y="10" width="12" height="10" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M9 10V7a3 3 0 0 1 6 0v3" stroke="currentColor" strokeWidth="2" />
      <path d="M12 14v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function ZoomIcon({ sign }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="10" cy="10" r="5" stroke="currentColor" strokeWidth="2" />
      <path d="M14 14l5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M7.5 10h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      {sign === "plus" && (
        <path d="M10 7.5v5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      )}
    </svg>
  );
}

function FitIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M8 4H4v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M16 4h4v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M8 20H4v-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M16 20h4v-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function CursorIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M5 4l7 16 2-7 6-2L5 4z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

export default function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onAddNode,
}) {
  const { fitView, screenToFlowPosition, zoomIn, zoomOut } = useReactFlow();
  const [locked, setLocked] = useState(false);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const type = event.dataTransfer.getData("application/workflow-node");
      if (!type) {
        return;
      }
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      onAddNode(type, position);
    },
    [screenToFlowPosition, onAddNode],
  );

  return (
    <div
      className="relative h-full w-full bg-[#090908]"
      onDrop={onDrop}
      onDragOver={onDragOver}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodesDraggable={!locked}
        nodesConnectable={!locked}
        elementsSelectable={!locked}
        panOnDrag={!locked}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        deleteKeyCode={["Delete", "Backspace"]}
        connectionLineStyle={{ stroke: "#2563eb", strokeWidth: 2 }}
      />

      <div className="pointer-events-auto absolute left-5 top-1/2 z-10 flex -translate-y-1/2 flex-col items-center gap-3 rounded-full border border-white/10 bg-[#111113]/95 p-2 shadow-2xl shadow-black/40">
        <ToolButton
          active={locked}
          label={locked ? "Deverrouiller" : "Verrouiller"}
          onClick={() => setLocked((value) => !value)}
        >
          <LockIcon />
        </ToolButton>
        <ToolButton label="Zoom avant" onClick={() => zoomIn()}>
          <ZoomIcon sign="plus" />
        </ToolButton>
        <ToolButton label="Zoom arriere" onClick={() => zoomOut()}>
          <ZoomIcon sign="minus" />
        </ToolButton>
        <ToolButton label="Voir tout" onClick={() => fitView({ padding: 0.3 })}>
          <FitIcon />
        </ToolButton>
        <ToolButton active={!locked} label="Curseur" onClick={() => setLocked(false)}>
          <CursorIcon />
        </ToolButton>
      </div>
    </div>
  );
}
