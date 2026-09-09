import { request } from "./http";

export function getGallery(projectId) {
  return request(`/api/projects/${encodeURIComponent(projectId)}/gallery`);
}
