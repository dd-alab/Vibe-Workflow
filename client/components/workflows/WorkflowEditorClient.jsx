"use client";

import { useEffect, useState } from "react";
import { WorkflowBuilder } from "workflow-builder";
import "reactflow/dist/style.css";
import "workflow-builder/dist/tailwind.css";

import { assetContentUrl } from "../../lib/api/assets";
import { getCharacter, listCharacters } from "../../lib/api/characters";
import { listConnectors } from "../../lib/api/connectors";
import {
  createWorkflowRun,
  getJob,
  getWorkflowRun,
} from "../../lib/api/jobs";
import {
  createWorkflow,
  getWorkflow,
  getWorkflowNodeDefinitions,
  updateWorkflow,
} from "../../lib/api/workflows";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

function nodeOutputsFromJobs(jobs) {
  return jobs.reduce((outputs, job) => {
    if (job.status !== "completed" || !job.node_id) {
      return outputs;
    }
    const assetId = job.output_asset_ids?.[0];
    if (!assetId) {
      return outputs;
    }
    return {
      ...outputs,
      [job.node_id]: {
        imageUrl: assetContentUrl(assetId),
      },
    };
  }, {});
}

function characterPreview(character) {
  if (!character) {
    return null;
  }
  const activePrompt = (character.prompt_versions ?? []).find(
    (prompt) => prompt.id === character.active_prompt_version_id,
  );
  return {
    name: character.name,
    shortTexts: (character.short_texts ?? []).map((item) => item.text),
    activePromptText: activePrompt?.text || "",
  };
}

export default function WorkflowEditorClient({ projectId, workflowId }) {
  const [workflow, setWorkflow] = useState(null);
  const [definitions, setDefinitions] = useState([]);
  const [connectorOptions, setConnectorOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [selectedCharacterId, setSelectedCharacterId] = useState("");
  const [selectedCharacter, setSelectedCharacter] = useState(null);
  const [run, setRun] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [runError, setRunError] = useState("");
  const nodeOutputs = nodeOutputsFromJobs(jobs);

  useEffect(() => {
    if (!selectedCharacterId) {
      setSelectedCharacter(null);
      return undefined;
    }
    let cancelled = false;
    getCharacter(projectId, selectedCharacterId)
      .then((loadedCharacter) => {
        if (!cancelled) {
          setSelectedCharacter(loadedCharacter);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setSelectedCharacter(null);
          setRunError(error.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, selectedCharacterId]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getWorkflow(projectId, workflowId),
      getWorkflowNodeDefinitions(),
      listCharacters(projectId),
      listConnectors(),
    ])
      .then(([
        loadedWorkflow,
        loadedDefinitions,
        loadedCharacters,
        loadedConnectors,
      ]) => {
        if (!cancelled) {
          setWorkflow(loadedWorkflow);
          setDefinitions(loadedDefinitions);
          setConnectorOptions(loadedConnectors);
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
      setRunError("Selectionnez un asset avant execution.");
      return;
    }
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
        background: true,
      });
      setRun(startedRun);
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
        connectorOptions={connectorOptions}
        nodeOutputs={nodeOutputs}
        characterPreview={characterPreview(selectedCharacter)}
        onChange={setWorkflow}
        onSave={handleSave}
        onRun={handleRun}
      />
      {(saveError || runError) && (
        <div
          role="alert"
          className="pointer-events-none fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-xl border border-red-500/20 bg-red-950/80 px-4 py-2 text-sm text-red-200"
        >
          {saveError || runError}
        </div>
      )}
    </div>
  );
}
