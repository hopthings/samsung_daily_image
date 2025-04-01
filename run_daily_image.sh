#!/bin/bash
# Script to run the Samsung Daily Image app with proper environment
# Used by launchd to run the app daily

# Record start time
echo "===== Starting Samsung Daily Image run at $(date) =====" >> "/Users/MattHopkins/Projects/Python/samsung_daily_image/daily_run.log"

# Path to project
PROJECT_DIR="/Users/MattHopkins/Projects/Python/samsung_daily_image"
cd "$PROJECT_DIR" || {
    echo "Failed to change directory to $PROJECT_DIR" >> "$PROJECT_DIR/daily_run.log"
    exit 1
}

# Check if virtual environment exists
if [ -d ".venv" ]; then
    PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
elif [ -d "venv" ]; then
    PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
else
    echo "Virtual environment not found at: $PROJECT_DIR/.venv or $PROJECT_DIR/venv" >> "$PROJECT_DIR/daily_run.log"
    exit 1
fi

# Verify python exists
if [ ! -x "$PYTHON_PATH" ]; then
    echo "Python executable not found at $PYTHON_PATH" >> "$PROJECT_DIR/daily_run.log"
    exit 1
fi

# Print environment info for debugging
echo "Using Python at: $PYTHON_PATH" >> "$PROJECT_DIR/daily_run.log"
echo "Current directory: $(pwd)" >> "$PROJECT_DIR/daily_run.log"
echo "PATH: $PATH" >> "$PROJECT_DIR/daily_run.log"

# Get TV IP from .env file
TV_IP=$(grep SAMSUNG_TV_IP "$PROJECT_DIR/.env" | cut -d= -f2)
echo "Samsung TV IP: $TV_IP" >> "$PROJECT_DIR/daily_run.log"

# Test connectivity to the TV
echo "Testing connection to TV..." >> "$PROJECT_DIR/daily_run.log"
ping -c 3 "$TV_IP" >> "$PROJECT_DIR/daily_run.log" 2>&1 || {
    echo "WARNING: Cannot ping the TV. It may be off or disconnected." >> "$PROJECT_DIR/daily_run.log"
}

# Wait a bit for network to stabilize
echo "Waiting 5 seconds for network..." >> "$PROJECT_DIR/daily_run.log"
sleep 5

# Run the app with the full path to Python in the virtual environment
# This avoids having to activate the virtual environment in the launchd context
"$PYTHON_PATH" "$PROJECT_DIR/main.py" >> "$PROJECT_DIR/daily_run.log" 2>&1
EXIT_CODE=$?

# Record completion
echo "Finished with exit code: $EXIT_CODE" >> "$PROJECT_DIR/daily_run.log"
echo "===== Completed at $(date) =====" >> "$PROJECT_DIR/daily_run.log"
echo "" >> "$PROJECT_DIR/daily_run.log"

exit $EXIT_CODE