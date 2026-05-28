"""Main Runner.

Owns crash supervision for the reconcile task. `main()` itself is just a
reconcile loop — recoverable exceptions are caught there, fatal ones bubble
up to this module's done-callback, which decides to respawn or exit.
"""

import asyncio
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.orchestrator import main
from app.routers import bridge, container, veth
from app.utils import (
    EVENT_LOCK,
    clear_config_dirty,
    clear_db_dirty,
    close_db,
    commit_db,
    flush_runtime_config_to_root,
    get_last_success_ts,
    get_logger,
    is_config_dirty,
    is_db_dirty,
)

_LOGGER = get_logger("runner")

MAX_FAIL_COUNT = 2

_crash_count = 0
_last_crash_ts: float = 0.0
_reconcile_task: asyncio.Task | None = None
_shutting_down = False


def _handle_task_result(task: asyncio.Task) -> None:
    global _crash_count, _last_crash_ts  # noqa: PLW0603
    if _shutting_down:
        return
    try:
        task.result()
    except asyncio.CancelledError:
        _LOGGER.info("Reconcile task cancelled")
        return
    except Exception:
        # If a successful tick happened since the last crash, treat this as a
        # fresh streak — reset the counter to zero before incrementing.
        if get_last_success_ts() > _last_crash_ts:
            _crash_count = 0
        _crash_count += 1
        _last_crash_ts = time.monotonic()
        _LOGGER.exception("Reconcile task crashed (count=%d)", _crash_count)
        if _crash_count > MAX_FAIL_COUNT:
            _LOGGER.exception("Crash count exceeded MAX_FAIL_COUNT; exiting process")
            asyncio.get_running_loop().call_soon(sys.exit, 1)
            return
        _spawn_reconcile_task()


def _spawn_reconcile_task() -> None:
    global _reconcile_task  # noqa: PLW0603
    _reconcile_task = asyncio.create_task(main())
    _reconcile_task.add_done_callback(_handle_task_result)


@asynccontextmanager
async def app_lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context: spawn reconcile task on startup, drain on shutdown."""
    global _shutting_down  # noqa: PLW0603
    _LOGGER.info("Lifespan started")
    _spawn_reconcile_task()

    yield

    _LOGGER.info("Shutting down lifespan")
    _shutting_down = True
    if _reconcile_task is not None:
        _reconcile_task.cancel()
        try:
            await _reconcile_task
        except asyncio.CancelledError:
            _LOGGER.info("Task cancelled during shutdown")

    # Final flush: write any pending state to mounted /root/config.json + db.json
    async with EVENT_LOCK:
        if is_config_dirty():
            flush_runtime_config_to_root()
            clear_config_dirty()
        if is_db_dirty():
            commit_db()
            clear_db_dirty()
        close_db()


app = FastAPI(lifespan=app_lifespan)

app.include_router(bridge.router)
app.include_router(container.router)
app.include_router(veth.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Show the app name."""
    return {"message": "OVS Network Orchestrator API"}
