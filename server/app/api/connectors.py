from typing import Annotated

from fastapi import APIRouter, Depends

from app.services.connector_service import ConnectorService

from .dependencies import get_connector_service

router = APIRouter(tags=["connectors"])
ConnectorServiceDependency = Annotated[
    ConnectorService, Depends(get_connector_service)
]


@router.get("/connectors")
def list_connectors(service: ConnectorServiceDependency) -> list[dict]:
    return service.list_connectors()


@router.post("/connectors/{connector_id}/check")
def check_connector(
    connector_id: str,
    service: ConnectorServiceDependency,
) -> dict:
    return service.check(connector_id)
