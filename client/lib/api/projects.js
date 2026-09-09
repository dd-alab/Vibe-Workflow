import { request } from "./http";

export function listProjects() {
  return request("/api/projects");
}

export function createProject(payload) {
  return request("/api/projects", { method: "POST", body: payload });
}

export function getProject(projectId) {
  return request(`/api/projects/${encodeURIComponent(projectId)}`);
}

export function updateProject(projectId, payload) {
  return request(`/api/projects/${encodeURIComponent(projectId)}`, {
    method: "PATCH",
    body: payload,
  });
}
