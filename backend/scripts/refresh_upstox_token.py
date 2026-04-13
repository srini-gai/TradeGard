#!/usr/bin/env python3
"""
Upstox access token refresh script.

Reads UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REFRESH_TOKEN from the
deployment .env file, fetches a fresh access token via Upstox OAuth2
refresh-token grant, writes UPSTOX_ACCESS_TOKEN back to the same .env,
then restarts the backend Docker container.

Run via cron at 3:00 AM IST (21:30 UTC) daily on the host server:
    30 21 * * * /usr/bin/python3 /docker/tradegard/app/backend/scripts/refresh_upstox_token.py
"""

import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import dotenv_values

# ---------------------------------------------------------------------------
# Paths (host-side, outside Docker)
# ---------------------------------------------------------------------------
ENV_FILE = Path("/docker/tradegard/.env")
LOG_DIR = Path("/var/log/tradeguard")
LOG_FILE = LOG_DIR / "token_refresh.log"
CONTAINER_NAME = "tradegard-backend"

UPSTOX_TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"

# ---------------------------------------------------------------------------
# Logging — writes to file AND stdout so cron email captures failures
# ---------------------------------------------------------------------------
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("upstox_token_refresh")


def load_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        raise FileNotFoundError(f".env not found at {ENV_FILE}")
    env = dotenv_values(ENV_FILE)
    missing = [k for k in ("UPSTOX_API_KEY", "UPSTOX_API_SECRET", "UPSTOX_REFRESH_TOKEN") if not env.get(k)]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")
    return dict(env)


def fetch_new_token(api_key: str, api_secret: str, refresh_token: str) -> str:
    """
    Call Upstox OAuth2 token endpoint with grant_type=refresh_token.
    Returns the new access_token string.
    """
    payload = {
        "client_id": api_key,
        "client_secret": api_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    resp = requests.post(UPSTOX_TOKEN_URL, data=payload, headers=headers, timeout=15)

    if resp.status_code != 200:
        raise RuntimeError(
            f"Upstox token endpoint returned {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"No access_token in response: {data}")

    return token


def update_env_file(new_token: str) -> None:
    """
    Replace (or append) UPSTOX_ACCESS_TOKEN in the .env file in-place.
    Only touches that one line; all other vars are preserved exactly.
    """
    content = ENV_FILE.read_text(encoding="utf-8")
    pattern = re.compile(r"^UPSTOX_ACCESS_TOKEN=.*$", re.MULTILINE)

    if pattern.search(content):
        updated = pattern.sub(f"UPSTOX_ACCESS_TOKEN={new_token}", content)
    else:
        # Key missing — append it
        updated = content.rstrip("\n") + f"\nUPSTOX_ACCESS_TOKEN={new_token}\n"

    ENV_FILE.write_text(updated, encoding="utf-8")
    logger.info(f"Updated UPSTOX_ACCESS_TOKEN in {ENV_FILE}")


def restart_container() -> None:
    """docker restart <container> — non-fatal if Docker isn't running."""
    result = subprocess.run(
        ["docker", "restart", CONTAINER_NAME],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode == 0:
        logger.info(f"Container '{CONTAINER_NAME}' restarted successfully")
    else:
        raise RuntimeError(
            f"docker restart failed (exit {result.returncode}): {result.stderr.strip()}"
        )


def main() -> int:
    logger.info("=" * 60)
    logger.info("Upstox token refresh started")

    try:
        env = load_env()
        logger.info("Loaded env vars from %s", ENV_FILE)

        new_token = fetch_new_token(
            api_key=env["UPSTOX_API_KEY"],
            api_secret=env["UPSTOX_API_SECRET"],
            refresh_token=env["UPSTOX_REFRESH_TOKEN"],
        )
        logger.info("New access token obtained (len=%d)", len(new_token))

        update_env_file(new_token)
        restart_container()

        logger.info("Token refresh complete")
        return 0

    except Exception as exc:
        logger.error("Token refresh FAILED: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
