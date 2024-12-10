"""API router to add a container to a bridge."""

from typing import Annotated, cast

from fastapi import APIRouter, Body, HTTPException

from app.orchestrator import add_iface_to_container
from app.schemas import ContainerInfo
from app.utils import ContainerInfoDict, validate_container

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
    payload = cast(ContainerInfoDict, container_info.model_dump())
    # Pre-validation check
    if not validate_container(container_id, payload):
        raise HTTPException(status_code=400, detail="Validation failed")

    # Add interface to container
    try:
        add_iface_to_container(container_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "success", "container_id": container_id}
