#!/bin/bash
# Simple wrapper script for TV power control
# Makes it easier to use from cron without worrying about Python paths

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the project directory
cd "$SCRIPT_DIR" || exit 1

# Check for Python virtual environment
if [ -d ".venv" ]; then
    PYTHON_PATH="$SCRIPT_DIR/.venv/bin/python"
elif [ -d "venv" ]; then
    PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
elif [ -d "env" ]; then
    PYTHON_PATH="$SCRIPT_DIR/env/bin/python"
else
    # Fall back to system Python if no virtual environment is found
    PYTHON_PATH=$(which python3 || which python)
fi

# Run the TV power control script with all arguments passed through
"$PYTHON_PATH" "$SCRIPT_DIR/tv_power.py" "$@"
exit $?