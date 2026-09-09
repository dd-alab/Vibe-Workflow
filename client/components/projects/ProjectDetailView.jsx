"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  createCharacter,
  listCharacters,
  updateCharacter,
} from "../../lib/api/characters";
import { getProject, updateProject } from "../../lib/api/projects";

function formatDate(value) {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function ArrowIcon() {
  return (
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
  );
}

export default function ProjectDetailView({ projectId }) {
  const router = useRouter();
  const [project, setProject] = useState(null);
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [characterName, setCharacterName] = useState("");
  const [createError, setCreateError] = useState("");
  const [creating, setCreating] = useState(false);
  const [renamingProject, setRenamingProject] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectError, setProjectError] = useState("");
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameName, setRenameName] = useState("");
  const [renameError, setRenameError] = useState("");
  const renameInputRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getProject(projectId), listCharacters(projectId)])
      .then(([loadedProject, loadedCharacters]) => {
        if (!cancelled) {
          setProject(loadedProject);
          setProjectName(loadedProject.name);
          setCharacters(loadedCharacters);
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
  }, [projectId, reloadKey]);

  useEffect(() => {
    if (renameTarget) {
      renameInputRef.current?.focus();
    }
  }, [renameTarget]);

  function retry() {
    setLoading(true);
    setReloadKey((key) => key + 1);
  }

  async function handleCreate(event) {
    event.preventDefault();
    const name = characterName.trim();
    if (!name) {
      setCreateError("Saisissez un nom de personnage.");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      const character = await createCharacter(projectId, { name });
      router.push(`/projects/${projectId}/characters/${character.id}`);
    } catch (error) {
      setCreateError(error.message);
    } finally {
      setCreating(false);
    }
  }

  async function handleProjectRename(event) {
    event.preventDefault();
    const name = projectName.trim();
    if (!name) {
      setProjectError("Saisissez un nom de projet.");
      return;
    }
    setProjectError("");
    try {
      const updated = await updateProject(projectId, {
        expected_revision: project.revision,
        name,
      });
      setProject(updated);
      setProjectName(updated.name);
      setRenamingProject(false);
    } catch (error) {
      setProjectError(error.message);
    }
  }

  function beginCharacterRename(character) {
    setRenameTarget(character);
    setRenameName(character.name);
    setRenameError("");
  }

  async function handleCharacterRename(event) {
    event.preventDefault();
    const name = renameName.trim();
    if (!name) {
      setRenameError("Saisissez un nom de personnage.");
      return;
    }
    try {
      const updated = await updateCharacter(projectId, renameTarget.id, {
        expected_revision: renameTarget.revision,
        name,
      });
      setCharacters((items) =>
        items.map((item) => (item.id === updated.id ? updated : item)),
      );
      setRenameTarget(null);
      setRenameError("");
    } catch (error) {
      setRenameError(error.message);
    }
  }

  if (loading) {
    return (
      <div className="grid min-h-[60vh] place-items-center text-sm text-zinc-400">
        Chargement du projet...
      </div>
    );
  }

  if (loadError) {
    return (
      <div role="alert" className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
        <p className="font-medium text-red-200">{loadError}</p>
        <button
          type="button"
          onClick={retry}
          className="mt-4 min-h-11 rounded-xl border border-white/10 px-4 text-sm font-medium hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
        >
          Reessayer
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <header>
        <Link
          href="/projects"
          className="inline-flex min-h-11 items-center text-sm text-zinc-400 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
        >
          Retour aux projets
        </Link>
        <div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent-soft">
              Projet
            </p>
            <h1 className="break-words [overflow-wrap:anywhere] text-3xl font-semibold tracking-tight text-white md:text-4xl">
              {project.name}
            </h1>
            <p className="mt-2 text-sm text-zinc-500">
              {characters.length}/30 fiches preparees
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Link
              href={`/projects/${projectId}/workflows`}
              className="inline-flex min-h-11 items-center justify-center rounded-xl border border-white/10 px-4 text-sm font-medium text-zinc-200 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
            >
              Workflows
            </Link>
            <button
              type="button"
              onClick={() => setRenamingProject((visible) => !visible)}
              className="min-h-11 self-start rounded-xl border border-white/10 px-4 text-sm font-medium text-zinc-200 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus lg:self-auto"
            >
              Renommer le projet
            </button>
          </div>
        </div>
      </header>

      {renamingProject && (
        <form
          onSubmit={handleProjectRename}
          className="rounded-2xl border border-accent/20 bg-accent/5 p-4"
        >
          <label className="block text-sm font-medium text-zinc-200">
            Nouveau nom du projet
            <input
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              maxLength={120}
              className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-black/40 px-4 text-white outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
          </label>
          <div className="mt-3 flex gap-2">
            <button
              type="submit"
              className="min-h-11 rounded-xl bg-accent px-4 text-sm font-semibold hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
            >
              Enregistrer
            </button>
            <button
              type="button"
              onClick={() => setRenamingProject(false)}
              className="min-h-11 rounded-xl px-4 text-sm text-zinc-400 hover:bg-white/5 hover:text-white"
            >
              Annuler
            </button>
          </div>
          {projectError && (
            <p role="alert" className="mt-3 text-sm text-red-300">
              {projectError}
            </p>
          )}
        </form>
      )}

      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-4 md:p-5">
        <div className="mb-3">
          <h2 className="text-lg font-semibold text-white">Nouveau personnage</h2>
          <p className="mt-1 text-sm text-zinc-500">
            Creez une fiche vide, puis ajoutez ses textes et ses prompts.
          </p>
        </div>
        <form onSubmit={handleCreate} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="min-w-0 flex-1 text-sm font-medium text-zinc-200">
            Nom du personnage
            <input
              value={characterName}
              onChange={(event) => setCharacterName(event.target.value)}
              maxLength={120}
              placeholder="Auguste melancolique"
              className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-black/40 px-4 text-white outline-none placeholder:text-zinc-600 focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
          </label>
          <button
            type="submit"
            disabled={creating}
            className="min-h-11 rounded-xl bg-accent px-5 text-sm font-semibold text-white hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
          >
            {creating ? "Creation..." : "Creer et ouvrir"}
          </button>
        </form>
        {createError && (
          <p role="alert" className="mt-3 text-sm text-red-300">
            {createError}
          </p>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-baseline justify-between gap-4">
          <h2 className="text-lg font-semibold text-white">Personnages</h2>
          <span className="text-xs tabular-nums text-zinc-500">
            {characters.length} fiche{characters.length > 1 ? "s" : ""}
          </span>
        </div>

        {characters.length === 0 ? (
          <div className="grid min-h-56 place-items-center rounded-2xl border border-dashed border-white/15 bg-white/[0.02] p-8 text-center">
            <div>
              <p className="text-lg font-medium text-zinc-200">
                Aucun personnage dans ce projet
              </p>
              <p className="mt-2 text-sm text-zinc-500">
                Creez la premiere fiche avec le formulaire ci-dessus.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {characters.map((character, index) => (
              <article
                key={character.id}
                className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"
              >
                <div className="flex items-start gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white/5 text-xs font-semibold tabular-nums text-zinc-500">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-medium text-white">
                      {character.name}
                    </h3>
                    <p className="mt-1 text-xs text-zinc-600">
                      Modifie le {formatDate(character.updated_at)}
                    </p>
                  </div>
                </div>
                <div className="mt-5 flex items-center gap-2 border-t border-white/5 pt-4">
                  <Link
                    href={`/projects/${projectId}/characters/${character.id}`}
                    aria-label={`Ouvrir la fiche de ${character.name}`}
                    className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-white/5 px-3 text-sm font-medium text-zinc-200 hover:bg-accent/10 hover:text-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
                  >
                    Ouvrir
                    <ArrowIcon />
                  </Link>
                  <button
                    type="button"
                    onClick={() => beginCharacterRename(character)}
                    aria-label={`Renommer ${character.name}`}
                    className="min-h-11 rounded-xl px-3 text-sm text-zinc-500 hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
                  >
                    Renommer
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {renameTarget && (
        <section className="rounded-2xl border border-accent/20 bg-accent/5 p-4">
          <form onSubmit={handleCharacterRename}>
            <label className="block text-sm font-medium text-zinc-200">
              Renommer {renameTarget.name}
            <input
              ref={renameInputRef}
              value={renameName}
                onChange={(event) => setRenameName(event.target.value)}
                maxLength={120}
                className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-black/40 px-4 text-white outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
              />
            </label>
            <div className="mt-3 flex gap-2">
              <button
                type="submit"
                className="min-h-11 rounded-xl bg-accent px-4 text-sm font-semibold hover:bg-accent-hover"
              >
                Enregistrer
              </button>
              <button
                type="button"
                onClick={() => setRenameTarget(null)}
                className="min-h-11 rounded-xl px-4 text-sm text-zinc-400 hover:bg-white/5"
              >
                Annuler
              </button>
            </div>
            {renameError && (
              <p role="alert" className="mt-3 text-sm text-red-300">
                {renameError}
              </p>
            )}
          </form>
        </section>
      )}
    </div>
  );
}
