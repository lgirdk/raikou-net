"""API router for bridge create/delete."""

from typing import Annotated, cast

from fastapi import APIRouter, Body, HTTPException

from app.orchestrator import init_bridge, remove_bridge
from app.schemas import BridgeInfo
from app.utils import (
    EVENT_LOCK,
    BridgeInfoDict,
    get_config,
    mark_config_dirty,
    save_runtime_config,
    validate_bridge,
)

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
    payload = cast("BridgeInfoDict", bridge_info.model_dump())
    # Pre-validation check

    if not validate_bridge(bridge_name, payload):
        raise HTTPException(
            status_code=400,
            detail="Bridge already exists with the same parent details",
        )

    # Init Bridge logic
    try:
        async with EVENT_LOCK:
            init_bridge(bridge_name, payload)

            # Update runner config only if bridge is added
            config = get_config()
            bridge_config = config["bridge"].setdefault(bridge_name, {})
            for key, value in payload.items():
                if key in bridge_config and isinstance(value, list):
                    bridge_config.setdefault(key, []).extend(value)
                    continue
                bridge_config[key] = value

            save_runtime_config()
            mark_config_dirty()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "success", "bridge_name": bridge_name}


@router.delete("/bridge/{bridge_name}")
async def remove_bridge_api(bridge_name: str) -> dict:
    """Remove an OVS/Linux bridge and all associated state.

    Deletes the bridge from the host, purges its DB rows, and drops it from
    the in-memory config so the reconcile loop does not recreate it.

    :param bridge_name: The bridge name to remove.
    :type bridge_name: str
    :raises HTTPException: 404 if the bridge is not in the config.
    :return: Success message.
    :rtype: dict
    """
    async with EVENT_LOCK:
        config = get_config()
        if bridge_name not in config.get("bridge", {}):
            raise HTTPException(status_code=404, detail="Bridge not found")
        remove_bridge(bridge_name)
        config.get("bridge", {}).pop(bridge_name, None)
        # Remove any container iface entries referencing this bridge from config
        for ifaces in config.get("container", {}).values():
            ifaces[:] = [i for i in ifaces if i.get("bridge") != bridge_name]
        save_runtime_config()
        mark_config_dirty()

    return {"status": "success", "bridge_name": bridge_name}
