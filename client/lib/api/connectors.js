import { request } from "./http";

export function listConnectors() {
  return request("/api/connectors");
}

export function checkConnector(connectorId) {
  return request(
    `/api/connectors/${encodeURIComponent(connectorId)}/check`,
    { method: "POST" },
  );
}
