"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { createProject, listProjects } from "../../lib/api/projects";

function formatDate(value) {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export default function ProjectsView() {
  const router = useRouter();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    let cancelled = false;
    listProjects()
      .then((items) => {
        if (!cancelled) {
          setProjects(items);
          setLoadError("");
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setLoadError(error.message);
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
  }, [reloadKey]);

  function retry() {
    setLoading(true);
    setReloadKey((key) => key + 1);
  }

  async function handleCreate(event) {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setFormError("Saisissez un nom de projet.");
      return;
    }
    setSubmitting(true);
    setFormError("");
    try {
      const project = await createProject({ name: trimmedName });
      router.push(`/projects/${project.id}`);
    } catch (error) {
      setFormError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent-soft">
            Bibliotheque locale
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">
            Projets
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-zinc-400">
            Une serie regroupe ses personnages, ses prompts et toute sa production.
          </p>
        </div>
        {!loading && !loadError && (
          <p className="text-sm tabular-nums text-zinc-500">
            {projects.length} projet{projects.length > 1 ? "s" : ""}
          </p>
        )}
      </header>

      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-4 md:p-5">
        <form onSubmit={handleCreate} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="min-w-0 flex-1 text-sm font-medium text-zinc-200">
            Nom du projet
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
              placeholder="Portraits du cirque"
              className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-black/40 px-4 text-white outline-none placeholder:text-zinc-600 focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
          </label>
          <button
            type="submit"
            disabled={submitting}
            className="min-h-11 rounded-xl bg-accent px-5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Creation..." : "Creer le projet"}
          </button>
        </form>
        {formError && (
          <p role="alert" className="mt-3 text-sm text-red-300">
            {formError}
          </p>
        )}
      </section>

      {loading && (
        <div className="grid min-h-52 place-items-center rounded-2xl border border-white/10 bg-white/[0.02] text-sm text-zinc-400">
          Chargement des projets...
        </div>
      )}

      {!loading && loadError && (
        <div role="alert" className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
          <p className="font-medium text-red-200">{loadError}</p>
          <button
            type="button"
            onClick={retry}
            className="mt-4 min-h-11 rounded-xl border border-white/10 px-4 text-sm font-medium text-white hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
          >
            Reessayer
          </button>
        </div>
      )}

      {!loading && !loadError && projects.length === 0 && (
        <div className="grid min-h-64 place-items-center rounded-2xl border border-dashed border-white/15 bg-white/[0.02] p-8 text-center">
          <div>
            <p className="text-lg font-medium text-zinc-200">
              Aucun projet pour le moment
            </p>
            <p className="mt-2 text-sm text-zinc-500">
              Nommez votre premiere serie pour commencer.
            </p>
          </div>
        </div>
      )}

      {!loading && !loadError && projects.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="group rounded-2xl border border-white/10 bg-white/[0.035] p-4 transition-colors hover:border-accent/40 hover:bg-accent/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h2 className="truncate font-semibold text-white">
                    {project.name}
                  </h2>
                  <p className="mt-1 text-sm text-zinc-500">
                    Modifie le {formatDate(project.updated_at)}
                  </p>
                </div>
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-white/10 text-zinc-400 transition-colors group-hover:border-accent/30 group-hover:text-accent-soft">
                  <svg
                    aria-hidden="true"
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path strokeLinecap="round" d="M5 12h14m-5-5 5 5-5 5" />
                  </svg>
                </span>
              </div>
              <div className="mt-4 flex items-center justify-between border-t border-white/5 pt-3 text-xs">
                <span className="text-zinc-500">Personnages</span>
                <span className="font-medium tabular-nums text-zinc-300">
                  {project.characters?.length ?? 0}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
