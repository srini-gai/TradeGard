"""Pytest hooks: keep defaults out of production code paths."""

import os

# AsyncIOScheduler + multiple TestClient lifecycles raises "Event loop is closed".
# Uvicorn (no pytest) leaves this unset → scheduler runs at 9:20 IST Mon–Fri.
os.environ["TRADEGUARD_SCHEDULER"] = "0"
