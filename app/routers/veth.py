"""API router to add a VETH pair to a bridge."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException

from app.orchestrator import create_veth_pair, remove_veth_pair
from app.schemas import VethPairInfo
from app.utils import (
    EVENT_LOCK,
    get_config,
    mark_config_dirty,
    save_runtime_config,
    validate_veth_pair,
)

router = APIRouter()


@router.post("/add_veth_pair")
async def add_veth_pair_api(
    veth_pair_id: Annotated[str, Body()], veth_pair_info: VethPairInfo
) -> dict:
    """Add a VETH link onto a bridge.

    This API will be used if we want to add VLAN translations onto a bridge.
    Or if we want to have a dangling pair.
    i.e. One end is attached to bridge the other end is dangling.
    This comes handy when working with LXC containers.

    The veth_pair_id is also used as a prefix while creating the pair.
    i.e. "vmap1" id would create a v0_vmap1:v1_vmap1 VETH pair.
    The ID cannot be more than 8 characters.

    :param veth_pair_id: VETH pair ID
    :type veth_pair_id: str
    :param veth_pair_info: VETH pair details, including target bridge and VLAN.
    :type veth_pair_info: VethPairInfo
    :raises HTTPException: error code 400, if payload validation fails
    :raises HTTPException: error code 500, if fails to add veth pair to the bridge.
    :return: Success message
    :rtype: dict
    """
    if not veth_pair_info.map:
        veth_pair_info.map = ":"

    # Pre-validation check
    if not validate_veth_pair(veth_pair_id, veth_pair_info.model_dump()):
        raise HTTPException(status_code=400, detail="Validation failed")

    # Create veth pair
    try:
        async with EVENT_LOCK:
            create_veth_pair(
                veth_pair_info.on,
                veth_pair_id,
                veth_pair_info.map,
                veth_pair_info.trunk,
            )

            config = get_config()
            cc_config = config["veth_pairs"].setdefault(veth_pair_id, {})
            cc_config.update(veth_pair_info.model_dump())

            save_runtime_config()
            mark_config_dirty()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "success", "veth_pair_id": veth_pair_id}


@router.delete("/veth/{veth_pair_id}")
async def remove_veth_pair_api(veth_pair_id: str) -> dict:
    """Remove a veth pair from its bridge and delete both ends.

    :param veth_pair_id: The veth pair prefix (<=8 chars).
    :type veth_pair_id: str
    :raises HTTPException: 404 if the veth pair is not in config.
    :return: Success message.
    :rtype: dict
    """
    config = get_config()
    if veth_pair_id not in config.get("veth_pairs", {}):
        raise HTTPException(status_code=404, detail="Veth pair not found")

    bridge: str = config["veth_pairs"][veth_pair_id]["on"]

    async with EVENT_LOCK:
        remove_veth_pair(veth_pair_id, bridge)
        del config["veth_pairs"][veth_pair_id]
        save_runtime_config()
        mark_config_dirty()

    return {"status": "success", "veth_pair_id": veth_pair_id}
