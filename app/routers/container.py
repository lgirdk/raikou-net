"""API router to add a container to a bridge."""

from typing import Annotated, cast

from fastapi import APIRouter, Body, HTTPException

from app.orchestrator import add_iface_to_container, remove_container_iface
from app.schemas import ContainerInfo, RemoveContainerIface
from app.utils import (
    EVENT_LOCK,
    ContainerInfoDict,
    get_all_container_ifaces,
    get_config,
    has_container_iface,
    mark_config_dirty,
    save_runtime_config,
    validate_container,
)

router = APIRouter()


@router.post("/add_container_iface")
async def add_iface_to_container_api(
    container_id: Annotated[str, Body()], container_info: ContainerInfo
) -> dict:
    """Attach a OVS/Linux Bridge link to target container.

    :param container_id: container name
    :type container_id: str
    :param container_info: container's information, including its bridge and
                           interface details.
    :type container_info: ContainerInfo
    :raises HTTPException: error code 400, if payload validation fails
    :raises HTTPException: error code 500, if failed to attach container to
                           a bridge
    :return: Success message.
    :rtype: dict
    """
    payload = cast("ContainerInfoDict", container_info.model_dump())
    # Pre-validation check
    if not validate_container(container_id, payload):
        raise HTTPException(status_code=400, detail="Validation failed")

    # Add interface to container
    try:
        async with EVENT_LOCK:
            add_iface_to_container(container_id, payload)

            # Add runner config only if container iface is added
            config = get_config()
            cc_config = config["container"].setdefault(container_id, [])
            cc_config.append(payload)

            save_runtime_config()
            mark_config_dirty()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "success", "container_id": container_id}


@router.delete("/container/{container_id}/iface")
async def remove_container_iface_api(
    container_id: str,
    body: RemoveContainerIface,
) -> dict:
    """Remove a single interface from a container.

    :param container_id: Container name.
    :type container_id: str
    :param body: Bridge and interface name to remove.
    :type body: RemoveContainerIface
    :raises HTTPException: 404 if the (bridge, container, iface) triple is not tracked.
    :return: Success message.
    :rtype: dict
    """
    if not has_container_iface(body.bridge, container_id, body.iface):
        raise HTTPException(status_code=404, detail="Interface not found")

    async with EVENT_LOCK:
        remove_container_iface(container_id, body.bridge, body.iface)

        config = get_config()
        iface_list = config.get("container", {}).get(container_id, [])
        config["container"][container_id] = [
            e
            for e in iface_list
            if not (e.get("bridge") == body.bridge and e.get("iface") == body.iface)
        ]
        if not config["container"][container_id]:
            del config["container"][container_id]

        save_runtime_config()
        mark_config_dirty()

    return {"status": "success", "container_id": container_id}


@router.delete("/container/{container_id}")
async def remove_container_api(container_id: str) -> dict:
    """Remove all interfaces for a container.

    Uses DB rows as the source of truth — removes every tracked (bridge, iface)
    for the container and drops the container key from config.

    :param container_id: Container name.
    :type container_id: str
    :raises HTTPException: 404 if the container has no tracked interfaces and is
                           not present in config.
    :return: Success message.
    :rtype: dict
    """
    config = get_config()
    db_rows = [r for r in get_all_container_ifaces() if r["container"] == container_id]
    in_config = container_id in config.get("container", {})
    if not db_rows and not in_config:
        raise HTTPException(status_code=404, detail="Container not found")

    async with EVENT_LOCK:
        for row in db_rows:
            remove_container_iface(container_id, row["bridge"], row["iface"])
        config.get("container", {}).pop(container_id, None)
        save_runtime_config()
        mark_config_dirty()

    return {"status": "success", "container_id": container_id}
