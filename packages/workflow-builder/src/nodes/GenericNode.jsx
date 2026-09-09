"use client";

import React from "react";
import { Handle, Position } from "reactflow";

function ParameterField({ parameter, value, onChange }) {
  const current = value ?? parameter.default ?? "";
  const handleChange = (event) => {
    let next = event.target.value;
    if (parameter.type === "integer") {
      next = next === "" ? null : Number.parseInt(next, 10);
      if (Number.isNaN(next)) {
        next = null;
      }
    }
    onChange(parameter.name, next);
  };

  if (parameter.type === "boolean") {
    return (
      <label className="flex items-center gap-2 text-xs text-zinc-300">
        <input
          type="checkbox"
          checked={Boolean(current)}
          onChange={(event) => onChange(parameter.name, event.target.checked)}
          className="h-3.5 w-3.5 accent-zinc-400"
        />
        {parameter.name}
      </label>
    );
  }

  return (
    <label className="block text-xs text-zinc-400">
      <span className="mb-1 block capitalize">{parameter.name}</span>
      <input
        type={parameter.type === "integer" ? "number" : "text"}
        value={current === null ? "" : String(current)}
        onChange={handleChange}
        className="min-h-8 w-full rounded-lg border border-white/10 bg-black/40 px-2 text-xs text-zinc-100 outline-none focus:border-accent-focus"
      />
    </label>
  );
}

export default function GenericNode({ data, selected }) {
  const { definition, parameters, connectorId, onChange } = data || {};
  const inputs = definition?.inputs || [];
  const outputs = definition?.outputs || [];

  return (
    <div
      className={`min-w-52 rounded-xl border bg-[#1c1a17] px-3 py-2 shadow-lg transition-colors ${
        selected
          ? "border-accent-focus ring-2 ring-accent-focus/30"
          : "border-white/10"
      }`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-sm font-normal text-zinc-100">
          {definition?.name || data?.type || "Noeud"}
        </span>
        {definition?.connectorRequired && (
          <span className="rounded bg-accent-soft/20 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-accent-soft">
            {connectorId || "Connecteur"}
          </span>
        )}
      </div>

      <div className="space-y-2">
        {(definition?.parameters || []).map((parameter) => (
          <ParameterField
            key={parameter.name}
            parameter={parameter}
            value={parameters?.[parameter.name]}
            onChange={onChange || (() => {})}
          />
        ))}
      </div>

      {inputs.map((port) => (
        <Handle
          key={`input-${port.name}`}
          type="target"
          position={Position.Left}
          id={port.name}
          className="!h-[5px] !w-[5px] !bg-zinc-300"
        />
      ))}
      {outputs.map((port) => (
        <Handle
          key={`output-${port.name}`}
          type="source"
          position={Position.Right}
          id={port.name}
          className="!h-[5px] !w-[5px] !bg-zinc-300"
        />
      ))}
    </div>
  );
}
