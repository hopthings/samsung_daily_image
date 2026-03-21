#!/bin/bash
# Wrapper script to run daily art upload with exponential backoff retry
#
# Usage: ./run_with_retry.sh [main.py arguments]
#
# On the first attempt, runs the full pipeline (generate, validate, upload).
# On retries, reuses the already-generated image so the TV doesn't show
# a sequence of different images.
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
GENERATED_IMAGE=""

# Find the most recently generated image from today (if any)
find_todays_image() {
    local today
    today=$(date +"%Y%m%d")
    # Look for upscaled images first (final output), then enhanced, then raw
    for dir in enhanced_images generated_images; do
        if [ -d "$dir" ]; then
            local latest
            latest=$(find "$dir" -name "art_${today}_*" -type f \
                ! -name "*_optimized*" \
                -printf '%T@ %p\n' 2>/dev/null \
                | sort -rn | head -1 | cut -d' ' -f2-)
            if [ -n "$latest" ]; then
                echo "$latest"
                return 0
            fi
        fi
    done
    return 1
}

echo "=========================================="
echo "Daily Art Upload with Retry"
echo "Max retries: $MAX_RETRIES"
echo "=========================================="

while [ $ATTEMPT -le $((MAX_RETRIES + 1)) ]; do
    if [ $ATTEMPT -gt 1 ]; then
        echo ""
        echo "=========================================="
        echo "RETRY ATTEMPT $ATTEMPT/$((MAX_RETRIES + 1))"
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

    if [ $ATTEMPT -eq 1 ]; then
        # First attempt: run the full pipeline
        python main.py "$@"
        EXIT_CODE=$?
    else
        # Retry: reuse the image from the first attempt if available
        if [ -z "$GENERATED_IMAGE" ]; then
            GENERATED_IMAGE=$(find_todays_image)
        fi

        if [ -n "$GENERATED_IMAGE" ] && [ -f "$GENERATED_IMAGE" ]; then
            echo "Reusing previously generated image: $GENERATED_IMAGE"
            # Skip generation, validation, enhancement, and upscaling —
            # just retry the upload with the existing image
            python main.py --image "$GENERATED_IMAGE" --enhance none --no-upscale --skip-validation "$@"
            EXIT_CODE=$?
        else
            echo "No existing image found, running full pipeline"
            python main.py "$@"
            EXIT_CODE=$?
        fi
    fi

    if [ $EXIT_CODE -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "SUCCESS on attempt $ATTEMPT"
        echo "=========================================="
        exit 0
    else
        echo ""
        echo "=========================================="
        echo "FAILED on attempt $ATTEMPT (exit code: $EXIT_CODE)"
        echo "=========================================="

        # After first failure, try to find the generated image for reuse
        if [ -z "$GENERATED_IMAGE" ]; then
            GENERATED_IMAGE=$(find_todays_image)
            if [ -n "$GENERATED_IMAGE" ]; then
                echo "Found image for retry reuse: $GENERATED_IMAGE"
            fi
        fi

        if [ $ATTEMPT -ge $((MAX_RETRIES + 1)) ]; then
            echo ""
            echo "=========================================="
            echo "All $((MAX_RETRIES + 1)) attempts failed"
            echo "=========================================="
            exit $EXIT_CODE
        fi
    fi

    ATTEMPT=$((ATTEMPT + 1))
done
