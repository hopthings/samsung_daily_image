#!/bin/bash
# TV Power Control Wrapper for Cron Jobs
# Usage: tv_power_wrapper.sh [ON|OFF]

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to script directory
cd "$SCRIPT_DIR" || exit 1

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found at $SCRIPT_DIR/.venv"
    exit 1
fi

# Run the simplified power control script
python tv_power_simple.py "$@"
exit_code=$?

# Log the result
if [ $exit_code -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - TV power $1 command succeeded"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - TV power $1 command failed with exit code $exit_code"
fi

exit $exit_code
