#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pip install --user -r requirements.txt
mkdir -p data
if [ -f .env ]; then set -a; . ./.env; set +a; fi
exec python -u -m bot.main
