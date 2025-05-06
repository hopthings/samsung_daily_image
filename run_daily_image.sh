#!/bin/bash
# Script to run the Samsung Daily Image app with proper environment
# Works on both macOS and Raspberry Pi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/daily_run.log"

# Record start time
echo "===== Starting Samsung Daily Image run at $(date) =====" >> "$LOG_FILE"

# Change to the project directory
cd "$SCRIPT_DIR" || {
    echo "Failed to change directory to $SCRIPT_DIR" >> "$LOG_FILE"
    exit 1
}

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
    if [ -z "$PYTHON_PATH" ]; then
        echo "No Python installation found" >> "$LOG_FILE"
        exit 1
    fi
    echo "Warning: No virtual environment found, using system Python at $PYTHON_PATH" >> "$LOG_FILE"
fi

# Verify python exists
if [ ! -x "$PYTHON_PATH" ]; then
    echo "Python executable not found at $PYTHON_PATH" >> "$LOG_FILE"
    exit 1
fi

# Print environment info for debugging
echo "Using Python at: $PYTHON_PATH" >> "$LOG_FILE"
echo "Current directory: $(pwd)" >> "$LOG_FILE"
echo "PATH: $PATH" >> "$LOG_FILE"

# Get TV IP from .env file
if [ -f "$SCRIPT_DIR/.env" ]; then
    TV_IP=$(grep -E "^SAMSUNG_TV_IP=" "$SCRIPT_DIR/.env" | cut -d= -f2 | tr -d '"' | tr -d "'")
    echo "Samsung TV IP: $TV_IP" >> "$LOG_FILE"
    
    # Test connectivity to the TV
    if [ -n "$TV_IP" ]; then
        echo "Testing connection to TV..." >> "$LOG_FILE"
        ping -c 3 "$TV_IP" >> "$LOG_FILE" 2>&1 || {
            echo "WARNING: Cannot ping the TV. It may be off or disconnected." >> "$LOG_FILE"
        }
        
        # Attempt to wake the TV using WOL
        if command -v wakeonlan >/dev/null 2>&1 || command -v etherwake >/dev/null 2>&1; then
            # Get TV MAC address from .env file if available
            TV_MAC=$(grep -E "^SAMSUNG_TV_MAC=" "$SCRIPT_DIR/.env" | cut -d= -f2 | tr -d '"' | tr -d "'")
            if [ -n "$TV_MAC" ]; then
                echo "Attempting to wake TV with MAC: $TV_MAC" >> "$LOG_FILE"
                if command -v wakeonlan >/dev/null 2>&1; then
                    wakeonlan "$TV_MAC" >> "$LOG_FILE" 2>&1
                elif command -v etherwake >/dev/null 2>&1; then
                    # etherwake is common on Raspberry Pi
                    etherwake "$TV_MAC" >> "$LOG_FILE" 2>&1
                fi
            else
                echo "TV MAC address not found in .env file, skipping wake-on-lan" >> "$LOG_FILE"
            fi
        else
            echo "wakeonlan/etherwake command not found, skipping TV wake attempt" >> "$LOG_FILE"
        fi
        
        # Wait for network and TV to stabilize
        echo "Waiting 30 seconds for TV to power on and network to stabilize..." >> "$LOG_FILE"
        sleep 30
        
        # Check if TV is responding after wait
        echo "Re-checking TV connection..." >> "$LOG_FILE"
        ping -c 3 "$TV_IP" >> "$LOG_FILE" 2>&1
    else
        echo "TV IP not found in .env file" >> "$LOG_FILE"
    fi
else
    echo ".env file not found at $SCRIPT_DIR/.env" >> "$LOG_FILE"
fi

# Run the app with Python
echo "Running main.py..." >> "$LOG_FILE"
"$PYTHON_PATH" "$SCRIPT_DIR/main.py" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# Record completion
echo "Finished with exit code: $EXIT_CODE" >> "$LOG_FILE"
echo "===== Completed at $(date) =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Optional: Retry logic (commented out by default)
# Uncomment the following block if you want to enable retries
# MAX_RETRIES=3
# RETRY_COUNT=0
#
# while [ "$EXIT_CODE" -ne 0 ] && [ "$RETRY_COUNT" -lt "$MAX_RETRIES" ]; do
#     RETRY_COUNT=$((RETRY_COUNT + 1))
#     echo "Attempt $RETRY_COUNT failed with exit code $EXIT_CODE. Retrying in 30 minutes..." >> "$LOG_FILE"
#     sleep 1800
#     echo "===== Retry #$RETRY_COUNT at $(date) =====" >> "$LOG_FILE"
#     "$PYTHON_PATH" "$SCRIPT_DIR/main.py" >> "$LOG_FILE" 2>&1
#     EXIT_CODE=$?
#     echo "Retry #$RETRY_COUNT finished with exit code: $EXIT_CODE" >> "$LOG_FILE"
# done

exit $EXIT_CODE