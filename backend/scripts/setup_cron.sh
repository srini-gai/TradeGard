#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_cron.sh — install the Upstox token-refresh cron job on the HOST
#
# Run once on the server after deployment:
#   bash /docker/tradegard/app/backend/scripts/setup_cron.sh
#
# What it does:
#   - Adds a cron job that fires at 21:30 UTC (= 03:00 IST) every day
#   - Logs stdout/stderr to /var/log/tradeguard/token_refresh.log
#   - Is idempotent: running it twice will not create a duplicate entry
# ---------------------------------------------------------------------------

set -euo pipefail

SCRIPT_PATH="/docker/tradegard/app/backend/scripts/refresh_upstox_token.py"
PYTHON_BIN="/usr/bin/python3"
LOG_FILE="/var/log/tradeguard/token_refresh.log"
CRON_MARKER="upstox_token_refresh"

# 21:30 UTC = 03:00 IST (UTC+5:30)
CRON_SCHEDULE="30 21 * * *"
CRON_JOB="${CRON_SCHEDULE} ${PYTHON_BIN} ${SCRIPT_PATH} >> ${LOG_FILE} 2>&1  # ${CRON_MARKER}"

# ---------------------------------------------------------------------------
# Create log directory if needed
# ---------------------------------------------------------------------------
mkdir -p /var/log/tradeguard
echo "Log directory: /var/log/tradeguard"

# ---------------------------------------------------------------------------
# Install dependencies on the host (script runs outside Docker)
# ---------------------------------------------------------------------------
echo "Installing Python dependencies for token refresh script..."
${PYTHON_BIN} -m pip install --quiet requests python-dotenv

# ---------------------------------------------------------------------------
# Add cron job (idempotent — skip if marker already present)
# ---------------------------------------------------------------------------
if crontab -l 2>/dev/null | grep -q "${CRON_MARKER}"; then
    echo "Cron job already installed (found marker '${CRON_MARKER}') — skipping."
else
    # Append to existing crontab (preserves other jobs)
    (crontab -l 2>/dev/null; echo "${CRON_JOB}") | crontab -
    echo "Cron job installed:"
    echo "  ${CRON_JOB}"
fi

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
echo ""
echo "Current crontab:"
crontab -l

echo ""
echo "Done. Token will refresh daily at 03:00 IST (21:30 UTC)."
echo "To test immediately:"
echo "  ${PYTHON_BIN} ${SCRIPT_PATH}"
