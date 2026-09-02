#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo apt-get update
sudo apt-get install -y python3-venv rtl-sdr alsa-utils

python3 -m venv "${PROJECT_DIR}/.venv"
"${PROJECT_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${PROJECT_DIR}/.venv/bin/python" -m pip install --editable "${PROJECT_DIR}"

echo
echo "Installed. Run:"
echo "  source '${PROJECT_DIR}/.venv/bin/activate'"
echo "  pocket-receiver"

