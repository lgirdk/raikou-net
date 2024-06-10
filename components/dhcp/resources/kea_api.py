"""To update KEA configuration over FAST API."""

# pylint: disable=import-error
# pylint: disable=W0622
# pylint: disable=too-few-public-methods
import json
import logging
import subprocess
from asyncio import Lock, wait_for
from pathlib import Path
from typing import Literal

import httpx
import uvicorn
from fastapi import FastAPI, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

_LOCK = Lock()
APP = FastAPI()

LOG_CONFIG = uvicorn.config.LOGGING_CONFIG
LOG_HANDLERS = {
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "filename": "/var/log/access.log",
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1024,
            "backupCount": 3,
        },
    },
}


class DHCPData(BaseModel):
    """DHCP Config Data."""

    board_id: str
    reservation_data: dict


def check_and_start_service(service: Literal["dhcp4", "dhcp6"]) -> None:
    """Check the status of the specified DHCP service and start it if inactive.

    This function runs the `keactrl status` command to check if the specified
    DHCP service (dhcp4 or dhcp6) is active. If the service is inactive, it
    calls `start_service` to start the service.

    :param service: The DHCP service to check and start if inactive.
                    Must be either "dhcp4" or "dhcp6".
    :type service: Literal["dhcp4", "dhcp6"]
    """
    try:
        # Run the `keactrl status` command and capture the output
        result = subprocess.run(
            ["keactrl", "status"], capture_output=True, text=True, check=True
        )
        output = result.stdout

        # Check the status of the specified service
        service_status = f"DHCPv{service[-1]} server: active" in output

        # If the specified service is inactive, start it
        if not service_status:
            start_service(service)

    except subprocess.CalledProcessError as e:
        logging.exception("Error checking status: %s", e.stderr)


def start_service(service: Literal["dhcp4", "dhcp6"]) -> None:
    """Start the specified DHCP service.

    This function runs the `keactrl start -s <service>` command to start the
    specified DHCP service (dhcp4 or dhcp6).

    :param service: The DHCP service to start. Must be either "dhcp4" or "dhcp6".
    :type service: Literal["dhcp4", "dhcp6"]
    """
    try:
        # Start the specified service (dhcp4 or dhcp6)
        subprocess.run(
            ["keactrl", "start", "-s", service],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logging.exception("Error starting %s service: %s", service, e.stderr)


def _update_reservation(data: DHCPData, mode: str) -> None:
    """Use to update DHCPv4/v6 reservation data for a board.

    :param data: DHCP options data per service pool
    :type data: DHCPData
    :param mode: IP address family, Can be either v4/v6
    :type mode: str
    :raises ValueError: In case DHCP settings do not get applied
    """
    # Hardcoding the path, since it runs on a Debian Image.
    fpath = f"/etc/kea/board-v{mode}-{data.board_id}.json"

    path = Path(fpath)
    Path(f"{fpath}.old").write_text(path.read_text(encoding="UTF-8"), encoding="UTF-8")

    # write new config
    if (
        "data" in data.reservation_data
        or "voice" in data.reservation_data
        or "oam" in data.reservation_data
    ):
        blocks = [json.dumps(i, indent=4) for i in data.reservation_data.values()]
        path.write_text(",\n".join(blocks), encoding="UTF-8")
    else:
        json.dump(data.reservation_data, path.open("w", encoding="UTF-8"), indent=4)

    # check if DHCPv4 is running before updating reservation
    if mode == "4":
        check_and_start_service("dhcp4")
    else:
        check_and_start_service("dhcp6")

    # reload the DHCP server via KEA Backend API.
    response = httpx.post(
        url="http://localhost:8000",
        json={"command": "config-reload", "service": [f"dhcp{mode}"]},
    )
    response.raise_for_status()
    # Turns out error messages on KEA don't throw an error code.
    output = response.json()
    if output[0]["result"] != 0:
        raise ValueError(output[0]["text"])


def rollback(data: DHCPData, mode: str) -> None:
    """Rollback DHCPv4/v6 configurations.

    :param data: DHCP options data per service pool
    :type data: DHCPData
    :param mode: IP address family, can be either v4/v6
    :type mode: str
    """
    fpath = f"/etc/kea/board-v{mode}-{data.board_id}.json"

    Path(fpath).write_text(
        Path(f"{fpath}.old").read_text(encoding="UTF-8"), encoding="UTF-8"
    )

    response = httpx.post(
        url="http://localhost:8000",
        json={"command": "config-reload", "service": [f"dhcp{mode}"]},
    )
    response.raise_for_status()


async def update_dhcp_reservations(data: DHCPData) -> None:
    """Update DHCPv4 reservations.

    :param data: DHCPv4 options data per service pool
    :type data: DHCPData
    """
    _update_reservation(data=data, mode="4")


async def update_dhcp6_reservations(data: DHCPData) -> None:
    """Update DHCPv6 reservations.

    :param data: DHCPv6 options data per service pool
    :type data: DHCPData
    """
    _update_reservation(data=data, mode="6")


@APP.post("/update_dhcp")
async def update_dhcp_with_lock(data: DHCPData) -> JSONResponse:
    """Update DHCPv4 server only if you have a lock.

    :param data: DHCPv4 options data per service pool
    :type data: DHCPData
    :raises HTTPException: 503, if lock to update is acquired by another request
    :raises HTTPException: 500, if configuration update times out
    :raises HTTPException: 512, if invalid configuration
    :return: KEA Server update response
    :rtype: JSONResponse
    """
    output = JSONResponse(content={"detail": "Success"})

    if _LOCK.locked():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service busy"
        )

    async with _LOCK:
        try:
            await wait_for(update_dhcp_reservations(data), timeout=15)
        except TimeoutError as exc:
            rollback(data, mode="4")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update request timed Out!!",
                headers={"exc-msg": f"{exc}"},
            ) from exc
        except ValueError as exc:
            rollback(data, mode="4")
            raise HTTPException(
                status_code=512,
                detail="Failed to update DHCP reservation.",
                headers={"kea-error": f"{exc}"},
            ) from exc
    return output


@APP.post("/update_dhcp6")
async def update_dhcp6_with_lock(data: DHCPData) -> JSONResponse:
    """Update DHCPv6 server only if you have a lock.

    :param data: DHCPv6 options data per service pool
    :type data: DHCPData
    :raises HTTPException: 503, if lock to update is acquired by another request
    :raises HTTPException: 500, if configuration update times out
    :raises HTTPException: 512, if invalid configuration
    :return: KEA Server update response
    :rtype: JSONResponse
    """
    output = JSONResponse(content={"detail": "Success"})

    if _LOCK.locked():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service busy"
        )

    async with _LOCK:
        try:
            await wait_for(update_dhcp6_reservations(data), timeout=15)
        except TimeoutError as exc:
            rollback(data, mode="6")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update request timed Out!!",
                headers={"exc-msg": f"{exc}"},
            ) from exc
        except ValueError as exc:
            rollback(data, mode="6")
            raise HTTPException(
                status_code=512,
                detail="Failed to update DHCP reservation.",
                headers={"kea-error": f"{exc}"},
            ) from exc

    return output


if __name__ == "__main__":
    LOG_CONFIG.update(LOG_HANDLERS)
    uvicorn.run(APP, port=8080, host="0.0.0.0", log_config=LOG_CONFIG)  # noqa: S104
