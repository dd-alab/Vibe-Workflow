"use client";

import Image from "next/image";
import { useState } from "react";

import {
  assetContentUrl,
  assetThumbnailUrl,
  exportAsset,
  selectAsset,
  updateAsset,
} from "../../lib/api/assets";

const CLASSIFICATION_LABELS = {
  neutral: "Neutre",
  favorite: "Favori",
  rejected: "Rejete",
};

function resultAssets(character) {
  return (character.assets ?? []).filter((asset) => asset.kind !== "reference");
}

function kindLabel(kind) {
  if (kind === "generation") {
    return "Generation";
  }
  if (kind === "upscale") {
    return "Upscale";
  }
  if (kind === "export") {
    return "Export";
  }
  return kind;
}

export default function ResultGrid({
  projectId,
  character,
  disabled,
  onCharacterChange,
  onBusyChange,
}) {
  const [mutatingAssetId, setMutatingAssetId] = useState(null);
  const [error, setError] = useState("");
  const [missingThumbnailIds, setMissingThumbnailIds] = useState([]);
  const assets = resultAssets(character);
  const controlsDisabled = disabled || mutatingAssetId !== null;

  async function mutate(asset, action) {
    if (controlsDisabled) {
      return;
    }
    setMutatingAssetId(asset.id);
    setError("");
    onBusyChange(true);
    try {
      const updated = await action();
      onCharacterChange(updated);
    } catch (mutationError) {
      setError(mutationError.message);
    } finally {
      setMutatingAssetId(null);
      onBusyChange(false);
    }
  }

  function classify(asset, classification) {
    void mutate(asset, () =>
      updateAsset(projectId, character.id, asset.id, {
        expected_revision: character.revision,
        classification,
      }),
    );
  }

  function select(asset) {
    void mutate(asset, () =>
      selectAsset(projectId, character.id, {
        expected_revision: character.revision,
        asset_id: asset.id,
      }),
    );
  }

  function exportResult(asset) {
    void mutate(asset, () =>
      exportAsset(projectId, character.id, {
        expected_revision: character.revision,
        asset_id: asset.id,
      }),
    );
  }

  function markThumbnailMissing(assetId) {
    setMissingThumbnailIds((ids) =>
      ids.includes(assetId) ? ids : [...ids, assetId],
    );
  }

  if (assets.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-white/10 p-5 text-sm text-zinc-600">
        Aucun resultat genere. Lancez un workflow pour alimenter cette grille.
      </p>
    );
  }

  return (
    <div>
      {error && (
        <p role="alert" className="mb-3 text-sm text-red-300">
          {error}
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {assets.map((asset, index) => {
          const selected = character.selected_asset_id === asset.id;
          const missing = missingThumbnailIds.includes(asset.id);
          const busy = mutatingAssetId === asset.id;
          return (
            <article
              key={asset.id}
              className={`overflow-hidden rounded-2xl border bg-black/25 ${
                selected ? "border-accent/60" : "border-white/10"
              }`}
            >
              {missing ? (
                <div className="grid aspect-square place-items-center bg-red-500/5 p-4 text-center text-xs leading-5 text-red-200">
                  Fichier ou miniature introuvable
                </div>
              ) : (
                <a
                  href={assetContentUrl(asset.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="relative block aspect-square bg-black/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-focus"
                >
                  <Image
                    unoptimized
                    fill
                    src={assetThumbnailUrl(asset.id)}
                    alt={`${kindLabel(asset.kind)} ${index + 1} pour ${character.name}`}
                    sizes="(min-width: 1280px) 18rem, (min-width: 640px) 50vw, 100vw"
                    onError={() => markThumbnailMissing(asset.id)}
                    className="object-contain"
                  />
                </a>
              )}
              <div className="space-y-3 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-white">
                      {kindLabel(asset.kind)} {index + 1}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {CLASSIFICATION_LABELS[asset.classification]}
                    </p>
                  </div>
                  {selected && (
                    <span className="rounded-full bg-accent/15 px-2 py-1 text-xs font-semibold text-accent-soft">
                      Selection
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-1.5">
                  {Object.keys(CLASSIFICATION_LABELS).map((classification) => (
                    <button
                      key={classification}
                      type="button"
                      disabled={controlsDisabled}
                      onClick={() => classify(asset, classification)}
                      className={`min-h-9 rounded-lg border px-2 text-xs disabled:cursor-not-allowed disabled:opacity-50 ${
                        asset.classification === classification
                          ? "border-accent/40 bg-accent/10 text-accent-soft"
                          : "border-white/10 text-zinc-400 hover:bg-white/5"
                      }`}
                    >
                      {CLASSIFICATION_LABELS[classification]}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={controlsDisabled || selected}
                    onClick={() => select(asset)}
                    className="min-h-10 flex-1 rounded-lg bg-accent px-3 text-xs font-semibold text-white hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {busy ? "Action..." : "Selectionner"}
                  </button>
                  <button
                    type="button"
                    disabled={controlsDisabled}
                    onClick={() => exportResult(asset)}
                    className="min-h-10 rounded-lg border border-white/10 px-3 text-xs text-zinc-300 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Exporter
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
