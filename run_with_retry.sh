#!/bin/bash
# Wrapper script to run daily art upload with exponential backoff retry
#
# Usage: ./run_with_retry.sh [main.py arguments]
#
# Retry schedule: 5min, 10min, 20min, 40min, 80min (total: ~2.6 hours)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found at $SCRIPT_DIR/.venv"
    exit 1
fi

# Retry configuration
MAX_RETRIES=5
RETRY_DELAY=300  # Start with 5 minutes (300 seconds)
ATTEMPT=1

echo "=========================================="
echo "Daily Art Upload with Retry"
echo "Max retries: $MAX_RETRIES"
echo "=========================================="

while [ $ATTEMPT -le $((MAX_RETRIES + 1)) ]; do
    if [ $ATTEMPT -gt 1 ]; then
        echo ""
        echo "=========================================="
        echo "🔄 RETRY ATTEMPT $ATTEMPT/$((MAX_RETRIES + 1))"
        echo "Waiting $(($RETRY_DELAY / 60)) minutes before retry..."
        echo "=========================================="
        sleep $RETRY_DELAY
        # Double the delay for next attempt (exponential backoff)
        RETRY_DELAY=$((RETRY_DELAY * 2))
    fi

    echo ""
    echo "=========================================="
    echo "Attempt $ATTEMPT: Running main.py"
    echo "=========================================="

    # Run the main script with all passed arguments
    python main.py "$@"
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "✓ SUCCESS on attempt $ATTEMPT"
        echo "=========================================="
        exit 0
    else
        echo ""
        echo "=========================================="
        echo "✗ FAILED on attempt $ATTEMPT (exit code: $EXIT_CODE)"
        echo "=========================================="

        if [ $ATTEMPT -ge $((MAX_RETRIES + 1)) ]; then
            echo ""
            echo "=========================================="
            echo "❌ All $((MAX_RETRIES + 1)) attempts failed"
            echo "=========================================="
            exit $EXIT_CODE
        fi
    fi

    ATTEMPT=$((ATTEMPT + 1))
done
