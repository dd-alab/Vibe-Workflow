import { request } from "./http";

function workflowsPath(projectId, workflowId = null) {
  const base = `/api/projects/${encodeURIComponent(projectId)}/workflows`;
  return workflowId
    ? `${base}/${encodeURIComponent(workflowId)}`
    : base;
}

export function listWorkflows(projectId) {
  return request(workflowsPath(projectId));
}

export function createWorkflow(projectId, payload) {
  return request(workflowsPath(projectId), {
    method: "POST",
    body: payload,
  });
}

export function getWorkflow(projectId, workflowId) {
  return request(workflowsPath(projectId, workflowId));
}

export function updateWorkflow(projectId, workflowId, payload) {
  return request(workflowsPath(projectId, workflowId), {
    method: "PUT",
    body: payload,
  });
}

export function deleteWorkflow(projectId, workflowId) {
  return request(workflowsPath(projectId, workflowId), {
    method: "DELETE",
  });
}

export function getWorkflowNodeDefinitions() {
  return request("/api/workflow-node-definitions");
}
