"""Main Runner."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.orchestrator import main
from app.routers import bridge, container, veth
from app.utils import get_logger

_LOGGER = get_logger("runner")


# Define the lifespan context manager
@asynccontextmanager
async def app_lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI.

    :param _app: fastapi context
    :type _app: FastAPI
    :yield: notifies FASTAPI to start listening to requests.
    """
    task = asyncio.create_task(main())

    # Yield allows FastAPI to start accepting requests
    yield

    # Shutdown logic: cancel the task when the app stops
    task.cancel()
    try:
        await task  # Wait for the task to finish gracefully after cancellation
    except asyncio.CancelledError:
        _LOGGER.info("Background task cancelled during shutdown.")


app = FastAPI(lifespan=app_lifespan)

app.include_router(bridge.router)
app.include_router(container.router)
app.include_router(veth.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Show the app name.

    :return: Hello banner
    :rtype: dict[str,str]
    """
    return {"message": "OVS Network Orchestrator API"}
