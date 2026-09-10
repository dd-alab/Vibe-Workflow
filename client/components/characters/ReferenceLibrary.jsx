"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import {
  assetContentUrl,
  assetThumbnailUrl,
  deleteReference,
  uploadReference,
} from "../../lib/api/assets";

let nextUploadId = 0;

function referenceAssets(character) {
  return (character.assets ?? []).filter((asset) => asset.kind === "reference");
}

export default function ReferenceLibrary({
  projectId,
  character,
  disabled,
  onCharacterChange,
  onBusyChange,
}) {
  const inputRef = useRef(null);
  const busyRef = useRef(false);
  const controllerRef = useRef(null);
  const dragDepthRef = useRef(0);
  const [isDragging, setIsDragging] = useState(false);
  const [uploads, setUploads] = useState([]);
  const [deletingAssetId, setDeletingAssetId] = useState(null);
  const [libraryError, setLibraryError] = useState("");
  const [missingThumbnailIds, setMissingThumbnailIds] = useState([]);
  const [announcement, setAnnouncement] = useState("");
  const references = referenceAssets(character);
  const controlsDisabled = disabled || busyRef.current;

  useEffect(() => {
    return () => controllerRef.current?.abort();
  }, []);

  function updateUpload(id, patch) {
    setUploads((items) =>
      items.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  }

  async function importFiles(fileList) {
    const files = Array.from(fileList ?? []);
    if (files.length === 0 || busyRef.current || disabled) {
      return;
    }
    const queued = files.map((file) => ({
      id: `upload-${nextUploadId++}`,
      file,
      name: file.name,
      status: "queued",
      progress: 0,
      error: "",
    }));
    setUploads(queued);
    setLibraryError("");
    busyRef.current = true;
    onBusyChange(true);
    const controller = new AbortController();
    controllerRef.current = controller;
    let currentCharacter = character;

    try {
      for (const [index, item] of queued.entries()) {
        updateUpload(item.id, { status: "uploading", progress: 0 });
        try {
          const updated = await uploadReference(
            projectId,
            currentCharacter.id,
            item.file,
            {
              expectedRevision: currentCharacter.revision,
              signal: controller.signal,
              onProgress: (progress) =>
                updateUpload(item.id, {
                  progress,
                  status: progress >= 100 ? "processing" : "uploading",
                }),
            },
          );
          currentCharacter = updated;
          onCharacterChange(updated);
          setUploads((items) => items.filter((upload) => upload.id !== item.id));
          setAnnouncement(`${item.name} a ete importe.`);
        } catch (error) {
          if (error.name === "AbortError") {
            return;
          }
          updateUpload(item.id, { status: "failed", error: error.message });
          if (error.status === 409) {
            setLibraryError(
              "La fiche a change. Rechargez-la avant de poursuivre les imports.",
            );
            for (const remaining of queued.slice(index + 1)) {
              updateUpload(remaining.id, {
                status: "failed",
                error: "Import interrompu apres un conflit de revision.",
              });
            }
            break;
          }
        }
      }
    } finally {
      busyRef.current = false;
      controllerRef.current = null;
      onBusyChange(false);
    }
  }

  function handleFileChange(event) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    void importFiles(files);
  }

  function handleDragEnter(event) {
    event.preventDefault();
    dragDepthRef.current += 1;
    if (!controlsDisabled) {
      setIsDragging(true);
    }
  }

  function handleDragLeave(event) {
    event.preventDefault();
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) {
      setIsDragging(false);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    dragDepthRef.current = 0;
    setIsDragging(false);
    void importFiles(event.dataTransfer.files);
  }

  async function handleDelete(asset, index) {
    if (
      controlsDisabled ||
      !window.confirm(`Supprimer la reference ${index + 1} de cette fiche ?`)
    ) {
      return;
    }
    busyRef.current = true;
    onBusyChange(true);
    setDeletingAssetId(asset.id);
    setLibraryError("");
    try {
      const updated = await deleteReference(
        projectId,
        character.id,
        asset.id,
        { expectedRevision: character.revision },
      );
      onCharacterChange(updated);
      setMissingThumbnailIds((ids) => ids.filter((id) => id !== asset.id));
      setAnnouncement(`La reference ${index + 1} a ete supprimee.`);
    } catch (error) {
      setLibraryError(error.message);
    } finally {
      busyRef.current = false;
      setDeletingAssetId(null);
      onBusyChange(false);
    }
  }

  function markThumbnailMissing(assetId) {
    setMissingThumbnailIds((ids) =>
      ids.includes(assetId) ? ids : [...ids, assetId],
    );
  }

  return (
    <div aria-busy={busyRef.current} aria-label="Bibliotheque de references">
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
        aria-label="Fichiers de reference"
        tabIndex={-1}
        className="sr-only"
        onChange={handleFileChange}
        disabled={controlsDisabled}
      />
      <div
        onDragEnter={handleDragEnter}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`rounded-2xl border border-dashed p-4 text-center transition-colors ${
          isDragging
            ? "border-accent bg-accent/10"
            : "border-white/15 bg-black/20"
        }`}
      >
        <p className="font-medium text-zinc-200">
          {isDragging ? "Deposez les images ici" : "Ajoutez vos images de reference"}
        </p>
        <p className="mt-2 text-sm text-zinc-500">
          PNG, JPEG ou WebP. Les fichiers sont copies dans le projet local.
        </p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={controlsDisabled}
          className="mt-3 min-h-11 min-w-40 whitespace-nowrap rounded-xl bg-accent px-6 text-sm font-semibold text-white hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
        >
          Choisir des images
        </button>
      </div>

      {uploads.length > 0 && (
        <div className="mt-3 space-y-2" aria-label="Imports en cours">
          {uploads.map((item) => (
            <div
              key={item.id}
              className="rounded-xl border border-white/10 bg-black/25 p-3"
            >
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="min-w-0 break-words text-zinc-300">
                  {item.name}
                </span>
                <span className="shrink-0 text-xs text-zinc-500">
                  {item.status === "queued" && "En attente"}
                  {item.status === "uploading" && `Import - ${item.progress} %`}
                  {item.status === "processing" && "Traitement de l'image..."}
                  {item.status === "failed" && "Echec"}
                </span>
              </div>
              {item.status === "uploading" && (
                <div
                  role="progressbar"
                  aria-label={`Import de ${item.name}`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={item.progress}
                  className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/5"
                >
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
              )}
              {item.error && (
                <p role="alert" className="mt-2 text-xs text-red-300">
                  {item.error}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {libraryError && (
        <p role="alert" className="mt-3 text-sm text-red-300">
          {libraryError}
        </p>
      )}
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      {references.length === 0 ? (
        <p className="mt-4 rounded-xl border border-dashed border-white/10 p-4 text-sm text-zinc-600">
          Aucune image de reference
        </p>
      ) : (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {references.map((asset, index) => {
            const missing = missingThumbnailIds.includes(asset.id);
            return (
              <article
                key={asset.id}
                className="overflow-hidden rounded-xl border border-white/10 bg-black/25"
              >
                {missing ? (
                  <div className="grid aspect-square place-items-center border border-red-500/20 bg-red-500/5 p-3 text-center text-xs leading-5 text-red-200">
                    <div>
                      <p>Fichier ou miniature introuvable</p>
                      <button
                        type="button"
                        onClick={() =>
                          setMissingThumbnailIds((ids) =>
                            ids.filter((id) => id !== asset.id),
                          )
                        }
                        className="mt-3 min-h-11 min-w-28 whitespace-nowrap rounded-lg border border-red-500/20 px-4 text-zinc-200 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
                      >
                        Reessayer
                      </button>
                    </div>
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
                      alt={`Reference ${index + 1} pour ${character.name}`}
                      sizes="(min-width: 1280px) 16rem, (min-width: 640px) 33vw, 50vw"
                      onError={() => markThumbnailMissing(asset.id)}
                      className="object-contain"
                    />
                  </a>
                )}
                <div className="p-3">
                  <p className="text-xs font-medium text-zinc-300">
                    Reference {index + 1}
                  </p>
                  <p className="mt-1 text-xs text-zinc-600">
                    {asset.width} x {asset.height} - {asset.media_type}
                  </p>
                  <button
                    type="button"
                    onClick={() => handleDelete(asset, index)}
                    disabled={controlsDisabled}
                    aria-label={`Supprimer la reference ${index + 1}`}
                    className="mt-3 min-h-11 w-full whitespace-nowrap rounded-lg border border-white/10 px-3 text-xs text-zinc-400 hover:border-red-500/25 hover:bg-red-500/5 hover:text-red-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {deletingAssetId === asset.id ? "Suppression..." : "Supprimer"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
