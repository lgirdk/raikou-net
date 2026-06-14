"""Typed async client for the Raikou-Net orchestrator REST API."""

import os

import httpx

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8080")


class OrchestratorClient:
    """Async wrapper around every orchestrator endpoint.

    Each method maps 1-to-1 to one orchestrator API call. Used by the
    proxy route today and by the AI/MCP layer in Phase 2.
    """

    def __init__(self, base_url: str = ORCHESTRATOR_URL) -> None:
        """Initialise the client.

        :param base_url: Base URL of the orchestrator (trailing slash stripped).
        """
        self._base = base_url.rstrip("/")

    async def get_config(self) -> dict:
        """Fetch the live in-memory topology config.

        :returns: The full config dict from the orchestrator.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self._base}/config")
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

    async def add_bridge(self, name: str, info: dict) -> dict:
        """POST /add_bridge.

        :param name: Name of the bridge to create.
        :param info: Bridge configuration dict.
        :returns: The orchestrator's JSON response.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self._base}/add_bridge",
                json={"bridge_name": name, "bridge_info": info},
            )
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

    async def add_container_iface(self, container_id: str, info: dict) -> dict:
        """POST /add_container_iface.

        :param container_id: Target container name or ID.
        :param info: Interface configuration dict.
        :returns: The orchestrator's JSON response.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self._base}/add_container_iface",
                json={"container_id": container_id, "container_info": info},
            )
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

    async def add_veth_pair(self, pair_id: str, info: dict) -> dict:
        """POST /add_veth_pair.

        :param pair_id: Identifier for the veth pair (≤8 chars).
        :param info: Veth pair configuration dict.
        :returns: The orchestrator's JSON response.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self._base}/add_veth_pair",
                json={"veth_pair_id": pair_id, "veth_pair_info": info},
            )
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

    async def remove_container_iface(
        self, container_id: str, bridge: str, iface: str
    ) -> dict:
        """DELETE /container/{id}/iface.

        :param container_id: Target container name or ID.
        :param bridge: Bridge the interface belongs to.
        :param iface: Interface name to remove.
        :returns: The orchestrator's JSON response.
        """
        async with httpx.AsyncClient() as client:
            r = await client.delete(
                f"{self._base}/container/{container_id}/iface",
                json={"bridge": bridge, "iface": iface},
            )
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

    async def remove_container(self, container_id: str) -> dict:
        """DELETE /container/{id}.

        :param container_id: Target container name or ID.
        :returns: The orchestrator's JSON response.
        """
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{self._base}/container/{container_id}")
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

    async def remove_veth_pair(self, pair_id: str) -> dict:
        """DELETE /veth/{id}.

        :param pair_id: Identifier of the veth pair to remove.
        :returns: The orchestrator's JSON response.
        """
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{self._base}/veth/{pair_id}")
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]
