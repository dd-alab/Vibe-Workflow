import { request } from "./http";

function characterPath(projectId, characterId = null) {
  const base = `/api/projects/${encodeURIComponent(projectId)}/characters`;
  return characterId
    ? `${base}/${encodeURIComponent(characterId)}`
    : base;
}

export function listCharacters(projectId) {
  return request(characterPath(projectId));
}

export function createCharacter(projectId, payload) {
  return request(characterPath(projectId), { method: "POST", body: payload });
}

export function getCharacter(projectId, characterId) {
  return request(characterPath(projectId, characterId));
}

export function updateCharacter(projectId, characterId, payload) {
  return request(characterPath(projectId, characterId), {
    method: "PATCH",
    body: payload,
  });
}

export function createPromptVersion(projectId, characterId, payload) {
  return request(`${characterPath(projectId, characterId)}/prompts`, {
    method: "POST",
    body: payload,
  });
}

export function activatePromptVersion(
  projectId,
  characterId,
  promptId,
  payload,
) {
  return request(
    `${characterPath(projectId, characterId)}/prompts/${encodeURIComponent(promptId)}/activate`,
    { method: "POST", body: payload },
  );
}
