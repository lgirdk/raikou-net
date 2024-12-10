"""API router to add bridge."""

from typing import Annotated, cast

from fastapi import APIRouter, Body, HTTPException

from app.orchestrator import init_bridge
from app.schemas import BridgeInfo
from app.utils import BridgeInfoDict, validate_bridge

router = APIRouter()


@router.post("/add_bridge")
async def init_bridge_api(
    bridge_name: Annotated[str, Body()], bridge_info: BridgeInfo
) -> dict:
    """Add a Linux/OVS bridge.

    :param bridge_name: bridge name
    :type bridge_name: str
    :param bridge_info: network details
    :type bridge_info: BridgeInfo
    :raises HTTPException: error code 400, if payload validation fails.
    :raises HTTPException: error code 500, if adding a bridge fails
    :return: Status Message
    :rtype: dict
    """
    payload = cast(BridgeInfoDict, bridge_info.model_dump())
    # Pre-validation check

    if not validate_bridge(bridge_name, payload):
        raise HTTPException(
            status_code=400,
            detail="Bridge already exists with the same parent details",
        )

    # Init Bridge logic
    try:
        init_bridge(bridge_name, payload)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "success", "bridge_name": bridge_name}
