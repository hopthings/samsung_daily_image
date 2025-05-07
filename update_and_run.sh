#!/bin/bash
set -euo pipefail

REPO_DIR="$HOME/Projects/samsung_daily_image"
VENV_DIR="$REPO_DIR/.venv"
LOGFILE="/var/log/samsung_daily_image.log"

cd "$REPO_DIR"

# 1. pull the newest commit
git pull --ff-only

# 2. create the venv once (cheap to test every run)
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# 3. activate and sync dependencies
source "$VENV_DIR/bin/activate"
pip install --quiet -r requirements.txt

# 4. run your own script
./run_daily_image.sh >> "$LOGFILE" 2>&1