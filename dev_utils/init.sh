#!/bin/bash
# seyoawe init script

set -e  # Immediately exit if any command fails


python3 mock_md_server.py&

echo "[INIT] Running poller.py to fetch modules and workflows..."
python3 poller.py
if [ $? -ne 0 ]; then
    echo "[ERROR] poller.py failed to run. Exiting."
    exit 1
fi
echo "[INIT] Starting web.py server..."
python3 koreflow.py
