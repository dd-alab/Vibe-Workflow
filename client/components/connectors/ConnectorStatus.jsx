"use client";

import { useEffect, useState } from "react";

import { checkConnector, listConnectors } from "../../lib/api/connectors";

function kindLabel(kind) {
  if (kind === "generation") {
    return "Generation";
  }
  if (kind === "upscale") {
    return "Upscale";
  }
  return kind;
}

export default function ConnectorStatus() {
  const [connectors, setConnectors] = useState([]);
  const [checks, setChecks] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    listConnectors()
      .then(async (items) => {
        const statuses = await Promise.all(
          items.map((connector) => checkConnector(connector.id)),
        );
        if (cancelled) {
          return;
        }
        setConnectors(items);
        setChecks(
          statuses.reduce((map, status) => {
            map[status.id] = status;
            return map;
          }, {}),
        );
        setError("");
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
  }, []);

  if (loading) {
    return (
      <div className="grid min-h-[60vh] place-items-center text-sm text-zinc-400">
        Verification des connecteurs...
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
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent-soft">
          Connecteurs
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">
          Fournisseurs de generation
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
          La page affiche seulement la disponibilite et la presence du secret,
          jamais la valeur de la cle API.
        </p>
      </header>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {connectors.map((connector) => {
          const check = checks[connector.id] || {};
          const configured = check.available || connector.capabilities?.configured;
          return (
            <article
              key={connector.id}
              className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-medium text-white">{connector.id}</h2>
                  <p className="mt-1 text-xs text-zinc-500">
                    {kindLabel(connector.kind)}
                  </p>
                </div>
                <span
                  className={`rounded-full border px-2 py-1 text-xs ${
                    configured
                      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"
                      : "border-zinc-500/25 bg-zinc-500/10 text-zinc-400"
                  }`}
                >
                  {configured ? "Pret" : "A configurer"}
                </span>
              </div>
              {"secret_present" in check && (
                <p className="mt-4 text-sm text-zinc-400">
                  Secret: {check.secret_present ? "present" : "absent"}
                </p>
              )}
              {check.message && (
                <p className="mt-2 text-sm leading-6 text-zinc-500">
                  {check.message}
                </p>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
