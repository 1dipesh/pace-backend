#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "python3.12 was not found. Install Python 3.12 first."
  exit 1
fi

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"

if [ ! -f .env ]; then
  cp .env.example .env
fi

echo "Pace backend dependencies installed."
echo "Next:"
echo "  docker compose up -d"
echo "  uvicorn app.main:app --reload"
