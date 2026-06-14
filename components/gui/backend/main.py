"""Raikou-Net GUI backend.

Responsibilities:
- Proxy /api/* → orchestrator (ORCHESTRATOR_URL env var).
- Serve the built React SPA from the static/ directory.
"""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8080")

app = FastAPI(docs_url=None, redoc_url=None)


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy(path: str, request: Request) -> Response:
    """Forward any /api/* request verbatim to the orchestrator.

    :param path: The URL path segment after /api/.
    :param request: The incoming FastAPI request object.
    :returns: The orchestrator's response forwarded to the caller.
    """
    body = await request.body()
    headers: dict[str, str] = {}
    if ct := request.headers.get("content-type"):
        headers["content-type"] = ct

    url = f"{ORCHESTRATOR_URL}/{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    async with httpx.AsyncClient() as client:
        upstream = await client.request(
            request.method,
            url,
            content=body,
            headers=headers,
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


# Static SPA — only mounted when the build output exists.
# During development the Vite dev server handles static files directly.
_static = Path(__file__).parent / "static"
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="static")
