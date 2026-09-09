import { request } from "./http";

export function createWorkflowRun(projectId, payload) {
  return request(
    `/api/projects/${encodeURIComponent(projectId)}/workflow-runs`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export function getWorkflowRun(runId) {
  return request(`/api/workflow-runs/${encodeURIComponent(runId)}`);
}

export function getJob(jobId) {
  return request(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function retryJob(jobId) {
  return request(`/api/jobs/${encodeURIComponent(jobId)}/retry`, {
    method: "POST",
  });
}

export function cancelJob(jobId) {
  return request(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
  });
}

export function listConnectors() {
  return request("/api/connectors");
}

export function checkConnector(connectorId) {
  return request(
    `/api/connectors/${encodeURIComponent(connectorId)}/check`,
    { method: "POST" },
  );
}
