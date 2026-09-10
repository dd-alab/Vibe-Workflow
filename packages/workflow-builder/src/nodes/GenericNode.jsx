"use client";

import React from "react";
import { Handle, Position } from "reactflow";

import { connectorRequired } from "../registry/nodeDefinitions";

function ParameterField({ parameter, value, onChange, fallbackValue }) {
  const current = value ?? parameter.default ?? "";
  const visibleValue = current === "" ? fallbackValue || "" : current;
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

  if (parameter.type === "text_list") {
    const items = Array.isArray(current) ? current : [];
    return (
      <div className="space-y-2">
        {items.map((item, index) => (
          <label key={index} className="block text-[10px] text-zinc-500">
            <span className="sr-only">Text item {index + 1}</span>
            <textarea
              value={item || ""}
              onChange={(event) => {
                const nextItems = [...items];
                nextItems[index] = event.target.value;
                onChange(parameter.name, nextItems);
              }}
              rows={2}
              className="min-h-16 w-full resize-y rounded-md border border-white/10 bg-black/20 px-3 py-2 text-[11px] font-semibold leading-4 text-zinc-100 outline-none placeholder:text-zinc-700 focus:border-accent-focus"
              placeholder="Text value"
            />
          </label>
        ))}
        <button
          type="button"
          className="text-[11px] font-semibold text-zinc-100 hover:text-accent-soft"
          onClick={() => onChange(parameter.name, [...items, ""])}
        >
          + Add another item
        </button>
      </div>
    );
  }

  if (parameter.name === "prompt_text" || parameter.name === "additional_text") {
    return (
      <label className="block text-[10px] text-zinc-500">
        <span className={parameter.name === "additional_text" ? "mb-1 block text-zinc-100" : "sr-only"}>
          {parameter.name === "additional_text" ? "Your text" : parameter.name}
        </span>
        <textarea
          value={current === null ? "" : String(visibleValue)}
          onChange={handleChange}
          rows={5}
          className="min-h-28 w-full resize-y border-0 bg-transparent p-0 text-[11px] font-semibold leading-4 text-zinc-100 outline-none placeholder:text-zinc-700"
          placeholder={
            parameter.name === "additional_text"
              ? "Write additional text"
              : "Input text..."
          }
        />
      </label>
    );
  }

  return (
    <label className="block text-[10px] text-zinc-500">
      <span className="mb-1 block uppercase tracking-wide">{parameter.name}</span>
      <input
        type={parameter.type === "integer" ? "number" : "text"}
        value={current === null ? "" : String(current)}
        onChange={handleChange}
        className="workflow-number-input min-h-7 w-full rounded-md border border-white/10 bg-black/40 px-2 text-[11px] text-zinc-100 outline-none focus:border-accent-focus"
      />
    </label>
  );
}

function nodeIcon(type) {
  if (type === "text_iterator") {
    return "T";
  }
  if (type === "prompt_concatenator") {
    return ">>";
  }
  if (type === "prompt_variant") {
    return "T";
  }
  if (["image_generation", "result_set", "selection", "upscale", "export"].includes(type)) {
    return "IMG";
  }
  return "IN";
}

function portColor(port) {
  if (port.type === "array" || port.name === "array") {
    return "!bg-zinc-200 !border-zinc-200";
  }
  if (port.type === "image" || port.name === "image") {
    return "!bg-[#1fbf75] !border-[#1fbf75]";
  }
  return "!bg-[#2563eb] !border-[#2563eb]";
}

function DuplicateIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="8" y="8" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M6 14H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v1" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 4v10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M8 10l4 4 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 20h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 7h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M10 11v6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M14 11v6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M6 7l1 13h10l1-13" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M9 7V4h6v3" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

export default function GenericNode({ data, selected }) {
  const {
    definition,
    parameters,
    connectorId,
    connectorOptions = [],
    onChange,
    onConnectorChange,
    onDuplicate,
    onDelete,
    preview,
    characterPreview,
  } = data || {};
  const inputs = definition?.inputs || [];
  const visibleInputs =
    definition?.type === "prompt_concatenator"
      ? Array.from(
          { length: Math.max(2, Number(parameters?.input_count || 2)) },
          (_, index) => ({ name: `prompt_${index + 1}`, type: "prompt" }),
        )
      : inputs;
  const outputs = definition?.outputs || [];
  const needsConnector = connectorRequired(definition);
  const [menuOpen, setMenuOpen] = React.useState(false);

  function deleteNode() {
    setMenuOpen(false);
    const confirmed = window.confirm(
      `Supprimer le noeud ${definition?.name || "node"} ?`,
    );
    if (confirmed) {
      onDelete?.();
    }
  }

  return (
    <div className="relative pt-5">
      <div className="absolute left-0 top-0 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
        {data?.visualLabel || "NODE"}
      </div>
      <div
        className={`min-w-64 max-w-72 rounded-xl border bg-[#0d0e10] shadow-2xl shadow-black/35 transition-colors ${
          selected
            ? "border-accent-focus ring-2 ring-accent-focus/30"
            : "border-white/10"
        }`}
      >
        <div className="flex items-center justify-between gap-2 border-b border-white/[0.06] px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <span className="grid h-5 min-w-5 place-items-center rounded-md bg-white/10 px-1 text-[9px] font-bold text-zinc-400">
              {nodeIcon(definition?.type)}
            </span>
            <span className="truncate text-xs font-semibold text-zinc-100">
              {definition?.name || data?.type || "Noeud"}
            </span>
          </div>
          <div className="relative">
            <button
              type="button"
              aria-label="Options du noeud"
              aria-expanded={menuOpen}
              onClick={(event) => {
                event.stopPropagation();
                setMenuOpen((value) => !value);
              }}
              className="rounded px-1 text-sm leading-none text-zinc-500 hover:bg-white/10 hover:text-zinc-200"
            >
              ...
            </button>
            {menuOpen && (
              <div className="nodrag absolute right-0 top-7 z-50 w-44 overflow-hidden rounded-md border border-white/10 bg-[#1a1b20] py-1 shadow-2xl shadow-black/50">
                <button
                  type="button"
                  className="flex min-h-9 w-full items-center gap-2 px-3 text-left text-[11px] font-semibold text-zinc-300 hover:bg-white/5"
                  onClick={(event) => {
                    event.stopPropagation();
                    setMenuOpen(false);
                    onDuplicate?.();
                  }}
                >
                  <span className="text-[#4f8cff]"><DuplicateIcon /></span>
                  Duplicate
                </button>
                {preview?.imageUrl && (
                  <a
                    href={preview.imageUrl}
                    download
                    className="flex min-h-9 w-full items-center gap-2 px-3 text-left text-[11px] font-semibold text-zinc-300 hover:bg-white/5"
                    onClick={(event) => {
                      event.stopPropagation();
                      setMenuOpen(false);
                    }}
                  >
                    <span className="text-[#1fbf75]"><DownloadIcon /></span>
                    Download
                  </a>
                )}
                <button
                  type="button"
                  className="flex min-h-9 w-full items-center gap-2 px-3 text-left text-[11px] font-semibold text-red-300 hover:bg-red-500/10"
                  onClick={(event) => {
                    event.stopPropagation();
                    deleteNode();
                  }}
                >
                  <span><TrashIcon /></span>
                  Delete Node
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-2 px-3 py-3">
          {definition?.type === "prompt_concatenator" && (
            <div className="min-h-28 rounded border border-white/10 bg-black/20 p-3 text-[11px] text-zinc-500">
              Connect multiple prompts to one output prompt.
            </div>
          )}

          {definition?.type === "text_iterator" && (
            <p className="text-[11px] leading-4 text-zinc-500">
              Iterate over a list of text values.
            </p>
          )}

          {definition?.type === "character_input" && (
            <div className="space-y-2 text-[11px] leading-4 text-zinc-200">
              {characterPreview?.name && (
                <p className="font-semibold text-zinc-100">
                  {characterPreview.name}
                </p>
              )}
              {(characterPreview?.shortTexts ?? []).length > 0 ? (
                <div className="space-y-1">
                  {characterPreview.shortTexts.slice(0, 3).map((text, index) => (
                    <p
                      key={`${index}-${text}`}
                      className="line-clamp-3 border-l border-accent/40 pl-2 text-zinc-300"
                    >
                      {text}
                    </p>
                  ))}
                </div>
              ) : (
                <p className="text-zinc-500">Aucun texte court charge.</p>
              )}
            </div>
          )}

        {needsConnector && (
          <label className="block text-[10px] text-zinc-500">
            <span className="mb-1 block uppercase tracking-wide">Connecteur</span>
            <select
              value={connectorId || ""}
              onChange={(event) => onConnectorChange?.(event.target.value)}
              className="min-h-7 w-full rounded-md border border-white/10 bg-black/40 px-2 text-[11px] text-zinc-100 outline-none focus:border-accent-focus"
            >
              <option value="">Choisir</option>
              {connectorOptions.map((connector) => (
                <option key={connector.id} value={connector.id}>
                  {connector.id}
                </option>
              ))}
            </select>
          </label>
        )}
        {(definition?.parameters || [])
          .filter((parameter) => !parameter.hidden)
          .map((parameter) => (
          <ParameterField
            key={parameter.name}
            parameter={parameter}
            value={parameters?.[parameter.name]}
            onChange={onChange || (() => {})}
            fallbackValue={
              parameter.name === "prompt_text"
                ? characterPreview?.activePromptText
                : ""
            }
            />
          ))}
          {definition?.type === "prompt_concatenator" && (
            <button
              type="button"
              className="mt-1 text-[11px] font-semibold text-zinc-100 hover:text-accent-soft"
              onClick={() =>
                onChange?.(
                  "input_count",
                  Math.max(2, Number(parameters?.input_count || 2)) + 1,
                )
              }
            >
              + Add text input
            </button>
          )}
          {definition?.type === "image_generation" && (
            preview?.imageUrl ? (
              <div className="border border-white/10 bg-black/25">
                <img
                  src={preview.imageUrl}
                  alt="Generated output"
                  className="block aspect-square w-full object-contain"
                  draggable={false}
                />
              </div>
            ) : (
              <div className="grid min-h-20 place-items-center border border-dashed border-white/10 bg-black/25 text-[11px] font-semibold text-zinc-400">
                Generated output
              </div>
            )
          )}
        </div>
      </div>

      {visibleInputs.map((port, index) => (
        <Handle
          key={`input-${port.name}`}
          type="target"
          position={Position.Left}
          id={port.name}
          className={`!h-[7px] !w-[7px] ${portColor(port)}`}
          style={
            definition?.type === "prompt_concatenator"
              ? { top: 78 + index * 38 }
              : undefined
          }
        />
      ))}
      {outputs.map((port) => (
        <Handle
          key={`output-${port.name}`}
          type="source"
          position={Position.Right}
          id={port.name}
          className={`!h-[7px] !w-[7px] ${portColor(port)}`}
        />
      ))}
    </div>
  );
}
