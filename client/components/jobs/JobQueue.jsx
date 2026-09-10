"use client";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

const STATUS_LABELS = {
  queued: "En attente",
  running: "En cours",
  completed: "Termine",
  failed: "Echec",
  cancelled: "Annule",
};

function statusLabel(status) {
  return STATUS_LABELS[status] ?? status ?? "Inconnu";
}

function statusClass(status) {
  if (status === "completed") {
    return "border-emerald-500/25 bg-emerald-500/10 text-emerald-200";
  }
  if (status === "failed") {
    return "border-red-500/25 bg-red-500/10 text-red-200";
  }
  if (status === "cancelled") {
    return "border-zinc-500/25 bg-zinc-500/10 text-zinc-300";
  }
  return "border-accent/25 bg-accent/10 text-accent-soft";
}

function formatDate(value) {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

export default function JobQueue({
  characters,
  selectedCharacterId,
  onSelectedCharacterIdChange,
  run,
  jobs,
  running,
  error,
  onCancelJob,
  onRetryJob,
}) {
  const isTerminal = run ? TERMINAL_STATUSES.has(run.status) : true;

  return (
    <aside className="pointer-events-auto fixed bottom-4 right-4 z-40 w-[min(24rem,calc(100vw-2rem))] rounded-2xl border border-white/10 bg-zinc-950/95 p-4 shadow-2xl shadow-black/40 backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-white">File locale</h2>
          <p className="mt-1 text-xs text-zinc-500">
            Execution mock, jobs persistants et polling local.
          </p>
        </div>
        {run && (
          <span
            className={`rounded-full border px-2.5 py-1 text-xs ${statusClass(run.status)}`}
          >
            {statusLabel(run.status)}
          </span>
        )}
      </div>

      <label className="mt-4 block text-xs font-medium text-zinc-300">
        Asset
        <select
          value={selectedCharacterId}
          onChange={(event) => onSelectedCharacterIdChange(event.target.value)}
          className="mt-2 min-h-10 w-full rounded-xl border border-white/10 bg-black/40 px-3 text-sm text-white outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
        >
          <option value="">Selectionner un asset</option>
          {characters.map((character) => (
            <option key={character.id} value={character.id}>
              {character.name}
            </option>
          ))}
        </select>
      </label>

      {error && (
        <p role="alert" className="mt-3 text-sm text-red-300">
          {error}
        </p>
      )}

      {run ? (
        <div className="mt-4 space-y-3">
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <div className="flex items-center justify-between gap-3 text-xs text-zinc-500">
              <span>Run</span>
              <span>{formatDate(run.updated_at)}</span>
            </div>
            <p className="mt-1 truncate text-sm text-zinc-200">{run.id}</p>
          </div>

          <div className="max-h-64 space-y-2 overflow-auto pr-1">
            {jobs.map((job) => (
              <article
                key={job.id}
                className="rounded-xl border border-white/10 bg-white/[0.03] p-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-medium text-white">
                    {job.node_id}
                  </p>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-xs ${statusClass(job.status)}`}
                  >
                    {statusLabel(job.status)}
                  </span>
                </div>
                <p className="mt-1 truncate text-xs text-zinc-500">
                  {job.connector_id}
                </p>
                {job.error && (
                  <p className="mt-2 text-xs text-red-300">{job.error}</p>
                )}
                <div className="mt-3 flex gap-2">
                  {!TERMINAL_STATUSES.has(job.status) && (
                    <button
                      type="button"
                      onClick={() => onCancelJob(job.id)}
                      className="min-h-9 rounded-lg border border-white/10 px-3 text-xs text-zinc-300 hover:bg-white/5"
                    >
                      Annuler
                    </button>
                  )}
                  {job.status === "failed" && (
                    <button
                      type="button"
                      onClick={() => onRetryJob(job.id)}
                      className="min-h-9 rounded-lg bg-accent px-3 text-xs font-semibold text-white hover:bg-accent-hover"
                    >
                      Reessayer
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-4 rounded-xl border border-dashed border-white/10 p-3 text-sm text-zinc-500">
          Choisissez un asset puis cliquez sur Executer.
        </p>
      )}

      {running && !isTerminal && (
        <p className="mt-3 text-xs text-zinc-500">Actualisation en cours...</p>
      )}
    </aside>
  );
}
