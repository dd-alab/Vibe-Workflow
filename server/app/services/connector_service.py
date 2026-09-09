from app.connectors import get_connector, list_connectors


class ConnectorService:
    def list_connectors(self) -> list[dict]:
        return list_connectors()

    def check(self, connector_id: str) -> dict:
        connector = get_connector(connector_id)
        return {
            "id": connector.id,
            "kind": connector.kind.value,
            "available": True,
            "capabilities": connector.capabilities,
            "estimated_cost": None,
        }
