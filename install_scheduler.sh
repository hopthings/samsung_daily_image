#!/bin/bash
# Script to install the LaunchAgent for Samsung Daily Image

# Check if LaunchAgent already exists
PLIST_DEST="$HOME/Library/LaunchAgents/com.matthopkins.samsungdailyimage.plist"
if [ -f "$PLIST_DEST" ]; then
    echo "Unloading existing LaunchAgent..."
    launchctl unload "$PLIST_DEST"
fi

# Copy the plist file to the LaunchAgents directory
echo "Installing LaunchAgent to $PLIST_DEST..."
cp com.matthopkins.samsungdailyimage.plist "$PLIST_DEST"

# Load the LaunchAgent
echo "Loading LaunchAgent..."
launchctl load "$PLIST_DEST"

# Check if it was loaded successfully
if launchctl list | grep com.matthopkins.samsungdailyimage > /dev/null; then
    echo "LaunchAgent installed and loaded successfully."
    echo "The script will run daily at 8:00 AM."
    echo "To test it immediately, run: launchctl start com.matthopkins.samsungdailyimage"
else
    echo "Failed to load the LaunchAgent. Please check for errors."
fi