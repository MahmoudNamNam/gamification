#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

VENV_DIR=".venv"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment in $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
fi

echo "Activating venv and installing dependencies ..."
source "$VENV_DIR/bin/activate"
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "Starting app (uvicorn app.main:app) ..."
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
