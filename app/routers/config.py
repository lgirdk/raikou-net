"""Read-only config endpoint."""

from fastapi import APIRouter

from app.utils import get_config

router = APIRouter()


@router.get("/config")
async def get_current_config() -> dict:
    """Return the live in-memory config.

    Pure read — no EVENT_LOCK needed. get_config() returns the
    in-memory dict; only the reconcile loop mutates it under the GIL.
    """
    return get_config()
