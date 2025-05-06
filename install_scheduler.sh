#!/bin/bash
# Cross-platform script to set up scheduled execution
# Supports macOS (launchd) and Linux/Raspberry Pi (crontab)

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_PATH="$SCRIPT_DIR/run_daily_image.sh"

# Make sure the run script is executable
chmod +x "$SCRIPT_PATH"

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - Use launchd
    echo "Setting up scheduled task on macOS using launchd..."
    
    PLIST_TEMPLATE="$SCRIPT_DIR/template.plist"
    PLIST_DEST="$HOME/Library/LaunchAgents/com.user.samsungdailyimage.plist"
    
    # Create the LaunchAgents directory if it doesn't exist
    mkdir -p "$HOME/Library/LaunchAgents"
    
    # Create a temporary plist file from template
    cat > "$SCRIPT_DIR/temp.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.samsungdailyimage</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_PATH</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/launchd.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>LANG</key>
        <string>en_US.UTF-8</string>
        <key>LC_ALL</key>
        <string>en_US.UTF-8</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

    # Check if LaunchAgent already exists
    if [ -f "$PLIST_DEST" ]; then
        echo "Unloading existing LaunchAgent..."
        launchctl unload "$PLIST_DEST"
    fi
    
    # Copy the temporary plist file to the LaunchAgents directory
    cp "$SCRIPT_DIR/temp.plist" "$PLIST_DEST"
    rm "$SCRIPT_DIR/temp.plist"
    
    # Load the LaunchAgent
    echo "Loading LaunchAgent..."
    launchctl load "$PLIST_DEST"
    
    # Check if it was loaded successfully
    if launchctl list | grep com.user.samsungdailyimage > /dev/null; then
        echo "LaunchAgent installed and loaded successfully."
        echo "The script will run daily at 8:00 AM."
        echo "To test it immediately, run: launchctl start com.user.samsungdailyimage"
    else
        echo "Failed to load the LaunchAgent. Please check for errors."
    fi
    
    # Rename the old plist if it exists
    if [ -f "$SCRIPT_DIR/com.matthopkins.samsungdailyimage.plist" ]; then
        mv "$SCRIPT_DIR/com.matthopkins.samsungdailyimage.plist" "$SCRIPT_DIR/old.plist"
        echo "Renamed old plist file to old.plist"
    fi
    
    # Clean up the old LaunchAgent if needed
    OLD_PLIST="$HOME/Library/LaunchAgents/com.matthopkins.samsungdailyimage.plist"
    if [ -f "$OLD_PLIST" ] && [ "$OLD_PLIST" != "$PLIST_DEST" ]; then
        echo "Removing old LaunchAgent..."
        launchctl unload "$OLD_PLIST" 2>/dev/null
        rm "$OLD_PLIST"
    fi
    
else
    # Linux/Raspberry Pi - Use crontab
    echo "Setting up scheduled task on Linux/Raspberry Pi using crontab..."
    
    # Check if it's already in crontab
    if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
        echo "Crontab entry already exists."
    else
        # Add to crontab
        (crontab -l 2>/dev/null; echo "0 8 * * * $SCRIPT_PATH") | crontab -
        echo "Added to crontab. The script will run daily at 8:00 AM."
    fi
    
    # Verify crontab entry
    if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
        echo "Crontab entry verified successfully."
    else
        echo "Failed to add crontab entry. Please check for errors."
    fi
fi

echo "Scheduler setup complete."
echo "Script location: $SCRIPT_PATH"