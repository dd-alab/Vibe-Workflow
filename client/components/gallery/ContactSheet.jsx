"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { assetThumbnailUrl } from "../../lib/api/assets";
import { getGallery } from "../../lib/api/gallery";
import { getProject } from "../../lib/api/projects";

export default function ContactSheet({ projectId }) {
  const [project, setProject] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [missingThumbnailIds, setMissingThumbnailIds] = useState([]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getProject(projectId), getGallery(projectId)])
      .then(([loadedProject, loadedItems]) => {
        if (!cancelled) {
          setProject(loadedProject);
          setItems(loadedItems);
          setError("");
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  function markThumbnailMissing(assetId) {
    setMissingThumbnailIds((ids) =>
      ids.includes(assetId) ? ids : [...ids, assetId],
    );
  }

  if (loading) {
    return (
      <div className="grid min-h-[60vh] place-items-center text-sm text-zinc-400">
        Chargement de la galerie...
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
        <p className="font-medium text-red-200">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <header>
        <div className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <span className="max-w-xl truncate font-medium text-zinc-200">
            {project?.name}
          </span>
          <Link
            href={`/projects/${projectId}`}
            className="text-zinc-400 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
          >
            Retour au projet
          </Link>
        </div>
        <div className="mt-2">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent-soft">
            Galerie
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">
            Planche contact
          </h1>
          <p className="mt-2 text-sm text-zinc-500">
            {items.length}/30 assets. Les cartes utilisent uniquement les miniatures.
          </p>
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {items.map((item, index) => {
          const asset = item.selected_asset;
          const missing = asset && missingThumbnailIds.includes(asset.id);
          return (
            <Link
              key={item.character_id}
              href={`/projects/${projectId}/characters/${item.character_id}`}
              className="group rounded-2xl border border-white/10 bg-white/[0.035] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
            >
              <div className="relative aspect-[4/5] bg-black/30">
                {asset && !missing ? (
                  <Image
                    unoptimized
                    fill
                    src={assetThumbnailUrl(asset.id)}
                    alt={`Image selectionnee pour ${item.character_name}`}
                    sizes="(min-width: 1280px) 20vw, (min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                    onError={() => markThumbnailMissing(asset.id)}
                    className="rounded-none object-cover transition duration-300 group-hover:scale-[1.02]"
                  />
                ) : (
                  <div className="grid h-full place-items-center p-4 text-center text-sm text-zinc-600">
                    {asset ? "Miniature introuvable" : "Aucune selection"}
                  </div>
                )}
                <span className="absolute left-3 top-3 rounded-full bg-black/60 px-2 py-1 text-xs font-semibold tabular-nums text-zinc-300">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </div>
              <div className="p-3">
                <h2 className="truncate text-sm font-medium text-white">
                  {item.character_name}
                </h2>
                <p className="mt-1 text-xs text-zinc-500">
                  {asset ? asset.kind : "Placeholder"}
                </p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
