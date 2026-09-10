"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  createWorkflow,
  deleteWorkflow,
  listWorkflows,
} from "../../lib/api/workflows";
import { getProject } from "../../lib/api/projects";

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

export default function WorkflowsView({ projectId }) {
  const router = useRouter();
  const [project, setProject] = useState(null);
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getProject(projectId), listWorkflows(projectId)])
      .then(([loadedProject, items]) => {
        if (!cancelled) {
          setProject(loadedProject);
          setWorkflows(items);
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

  function retry() {
    setReloadKey((key) => key + 1);
  }

  async function handleCreate(event) {
    event.preventDefault();
    const workflowName = name.trim();
    if (!workflowName) {
      setCreateError("Saisissez un nom de workflow.");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      const workflow = await createWorkflow(projectId, {
        name: workflowName,
        nodes: [],
        edges: [],
      });
      router.push(
        `/projects/${projectId}/workflows/${workflow.id}`,
      );
    } catch (error) {
      setCreateError(error.message);
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(workflow) {
    setDeletingId(workflow.id);
    try {
      await deleteWorkflow(projectId, workflow.id);
      setWorkflows((items) =>
        items.filter((item) => item.id !== workflow.id),
      );
    } catch (error) {
      setLoadError(error.message);
    } finally {
      setDeletingId(null);
    }
  }

  if (loading) {
    return (
      <div className="grid min-h-[60vh] place-items-center text-sm text-zinc-400">
        Chargement des workflows...
      </div>
    );
  }

  if (loadError && workflows.length === 0) {
    return (
      <div role="alert" className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
        <p className="font-medium text-red-200">{loadError}</p>
        <button
          type="button"
          onClick={retry}
          className="mt-4 min-h-11 min-w-32 whitespace-nowrap rounded-xl border border-white/10 px-5 text-sm font-medium hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
        >
          Reessayer
        </button>
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
            Workflows
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">
            Workflows locaux
          </h1>
        </div>
      </header>

      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-4 md:p-5">
        <div className="mb-3">
          <h2 className="text-lg font-semibold text-white">Nouveau workflow</h2>
          <p className="mt-1 text-sm text-zinc-500">
            Creez un workflow nodal, puis reliez les noeuds entre eux.
          </p>
        </div>
        <form onSubmit={handleCreate} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="min-w-0 flex-1 text-sm font-medium text-zinc-200">
            Nom du workflow
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
              placeholder="Portrait puis upscale"
              className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-black/40 px-4 text-white outline-none placeholder:text-zinc-600 focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
          </label>
          <button
            type="submit"
            disabled={creating}
            className="min-h-11 min-w-40 whitespace-nowrap rounded-xl bg-accent px-6 text-sm font-semibold text-white hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
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
          <h2 className="text-lg font-semibold text-white">Workflows</h2>
          <span className="text-xs tabular-nums text-zinc-500">
            {workflows.length}
          </span>
        </div>

        {workflows.length === 0 ? (
          <div className="grid min-h-56 place-items-center rounded-2xl border border-dashed border-white/15 bg-white/[0.02] p-8 text-center">
            <div>
              <p className="text-lg font-medium text-zinc-200">
                Aucun workflow dans ce projet
              </p>
              <p className="mt-2 text-sm text-zinc-500">
                Creez le premier workflow avec le formulaire ci-dessus.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {workflows.map((workflow) => (
              <article
                key={workflow.id}
                className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"
              >
                <h3 className="truncate font-medium text-white">
                  {workflow.name}
                </h3>
                <p className="mt-1 text-xs text-zinc-600">
                  {workflow.nodes.length} noeud
                  {workflow.nodes.length > 1 ? "s" : ""} - modifie le{" "}
                  {formatDate(workflow.updated_at)}
                </p>
                <div className="mt-5 flex items-center gap-2 border-t border-white/5 pt-4">
                  <Link
                    href={`/projects/${projectId}/workflows/${workflow.id}`}
                    aria-label={`Ouvrir le workflow ${workflow.name}`}
                    className="inline-flex min-h-11 min-w-32 flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-xl bg-white/5 px-4 text-sm font-medium text-zinc-200 hover:bg-accent/10 hover:text-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
                  >
                    Ouvrir
                    <ArrowIcon />
                  </Link>
                  <button
                    type="button"
                    disabled={deletingId === workflow.id}
                    onClick={() => handleDelete(workflow)}
                    aria-label={`Supprimer ${workflow.name}`}
                    className="min-h-11 min-w-28 whitespace-nowrap rounded-xl px-4 text-sm text-zinc-500 hover:bg-white/5 hover:text-red-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Supprimer
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
