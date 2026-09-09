import { request, uploadRequest } from "./http";

function referencePath(projectId, characterId) {
  return `/api/projects/${encodeURIComponent(projectId)}/characters/${encodeURIComponent(characterId)}/references`;
}

export function uploadReference(
  projectId,
  characterId,
  file,
  { expectedRevision, onProgress, signal } = {},
) {
  const formData = new FormData();
  formData.append("expected_revision", String(expectedRevision));
  formData.append("file", file);
  return uploadRequest(referencePath(projectId, characterId), formData, {
    onProgress,
    signal,
  });
}

export function deleteReference(
  projectId,
  characterId,
  assetId,
  { expectedRevision } = {},
) {
  const path = `${referencePath(projectId, characterId)}/${encodeURIComponent(assetId)}?expected_revision=${encodeURIComponent(expectedRevision)}`;
  return request(path, { method: "DELETE" });
}

export function assetThumbnailUrl(assetId) {
  return `/api/assets/${encodeURIComponent(assetId)}/thumbnail`;
}

export function assetContentUrl(assetId) {
  return `/api/assets/${encodeURIComponent(assetId)}/content`;
}
