from .base import Connector
from .mock_generation import MockGenerationConnector
from .mock_upscale import MockUpscaleConnector
from .muapi import MuApiGenerationConnector, MuApiUpscaleConnector

CONNECTORS: dict[str, Connector] = {
    MockGenerationConnector.id: MockGenerationConnector(),
    MockUpscaleConnector.id: MockUpscaleConnector(),
    MuApiGenerationConnector.id: MuApiGenerationConnector(),
    MuApiUpscaleConnector.id: MuApiUpscaleConnector(),
}


def get_connector(connector_id: str) -> Connector:
    connector = CONNECTORS.get(connector_id)
    if connector is None:
        raise ValueError(f"connector '{connector_id}' is unknown")
    return connector


def list_connectors() -> list[dict]:
    return [
        {
            "id": connector.id,
            "kind": connector.kind.value,
            "capabilities": connector.capabilities,
        }
        for connector in CONNECTORS.values()
    ]
