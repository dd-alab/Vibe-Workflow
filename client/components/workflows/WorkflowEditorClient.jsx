"use client";

import { useEffect, useState } from "react";
import { WorkflowBuilder } from "workflow-builder";
import "reactflow/dist/style.css";
import "workflow-builder/dist/tailwind.css";

import JobQueue from "../jobs/JobQueue";
import { listCharacters } from "../../lib/api/characters";
import {
  cancelJob,
  createWorkflowRun,
  getJob,
  getWorkflowRun,
  retryJob,
} from "../../lib/api/jobs";
import {
  createWorkflow,
  getWorkflow,
  getWorkflowNodeDefinitions,
  updateWorkflow,
} from "../../lib/api/workflows";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

export default function WorkflowEditorClient({ projectId, workflowId }) {
  const [workflow, setWorkflow] = useState(null);
  const [definitions, setDefinitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [characters, setCharacters] = useState([]);
  const [selectedCharacterId, setSelectedCharacterId] = useState("");
  const [run, setRun] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getWorkflow(projectId, workflowId),
      getWorkflowNodeDefinitions(),
      listCharacters(projectId),
    ])
      .then(([loadedWorkflow, loadedDefinitions, loadedCharacters]) => {
        if (!cancelled) {
          setWorkflow(loadedWorkflow);
          setDefinitions(loadedDefinitions);
          setCharacters(loadedCharacters);
          setSelectedCharacterId((current) =>
            current || loadedCharacters[0]?.id || "",
          );
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
  }, [projectId, workflowId]);

  useEffect(() => {
    if (!run?.id) {
      return undefined;
    }
    let cancelled = false;
    let timeoutId = null;

    async function refresh() {
      try {
        const latestRun = await getWorkflowRun(run.id);
        if (cancelled) {
          return;
        }
        setRun(latestRun);
        const loadedJobs = await Promise.all(
          (latestRun.job_ids ?? []).map((jobId) => getJob(jobId)),
        );
        if (cancelled) {
          return;
        }
        setJobs(loadedJobs);
        if (!TERMINAL_STATUSES.has(latestRun.status)) {
          timeoutId = window.setTimeout(refresh, 2000);
        }
      } catch (error) {
        if (!cancelled) {
          setRunError(error.message);
        }
      }
    }

    refresh();
    return () => {
      cancelled = true;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [run?.id]);

  async function handleSave() {
    setSaving(true);
    setSaveError("");
    try {
      const saved = workflow.id
        ? await updateWorkflow(projectId, workflow.id, workflow)
        : await createWorkflow(projectId, workflow);
      setWorkflow(saved);
    } catch (error) {
      setSaveError(error.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleRun(currentWorkflow) {
    if (!selectedCharacterId) {
      setRunError("Selectionnez un personnage avant execution.");
      return;
    }
    setRunning(true);
    setRunError("");
    try {
      const saved = currentWorkflow.id
        ? await updateWorkflow(projectId, currentWorkflow.id, currentWorkflow)
        : await createWorkflow(projectId, currentWorkflow);
      setWorkflow(saved);
      setJobs([]);
      const startedRun = await createWorkflowRun(projectId, {
        workflow_id: saved.id,
        character_id: selectedCharacterId,
      });
      setRun(startedRun);
    } catch (error) {
      setRunError(error.message);
    } finally {
      setRunning(false);
    }
  }

  async function handleCancelJob(jobId) {
    setRunError("");
    try {
      const updated = await cancelJob(jobId);
      setJobs((items) =>
        items.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (error) {
      setRunError(error.message);
    }
  }

  async function handleRetryJob(jobId) {
    setRunError("");
    try {
      const retried = await retryJob(jobId);
      setJobs((items) => [...items, retried]);
    } catch (error) {
      setRunError(error.message);
    }
  }

  if (loading) {
    return (
      <div className="grid min-h-[60vh] place-items-center text-sm text-zinc-400">
        Chargement du workflow...
      </div>
    );
  }

  if (loadError) {
    return (
      <div role="alert" className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
        <p className="font-medium text-red-200">{loadError}</p>
      </div>
    );
  }

  return (
    <div className="-mx-4 h-[calc(100dvh-2.5rem)] sm:-mx-6 md:-mx-8">
      <WorkflowBuilder
        workflow={workflow}
        nodeDefinitions={definitions}
        onChange={setWorkflow}
        onSave={handleSave}
        onRun={handleRun}
      />
      <JobQueue
        characters={characters}
        selectedCharacterId={selectedCharacterId}
        onSelectedCharacterIdChange={setSelectedCharacterId}
        run={run}
        jobs={jobs}
        running={running}
        error={runError}
        onCancelJob={handleCancelJob}
        onRetryJob={handleRetryJob}
      />
      {saveError && (
        <div
          role="alert"
          className="pointer-events-none fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-xl border border-red-500/20 bg-red-950/80 px-4 py-2 text-sm text-red-200"
        >
          {saveError}
        </div>
      )}
    </div>
  );
}
