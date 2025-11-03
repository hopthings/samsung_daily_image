# Samsung Frame TV Power Control

## Overview
The `tv_power.py` script provides reliable power control for Samsung Frame TVs, with special handling for art mode to ensure proper display of artwork.

## Features
- **Power ON**: Turns TV on and ensures art mode is active
- **Power OFF**: Completely powers off the TV (no display)
- **Wake-on-LAN**: Automatically wakes TV from deep sleep if configured
- **Network stability checks**: Verifies TV connectivity before operations
- **Art mode management**: Properly enables/disables art mode during power transitions
- **Cron-friendly**: Silent operation with proper exit codes
- **Robust error handling**: Graceful failure with informative messages

## Installation

1. Install the required library (if not already installed):
```bash
pip install wakeonlan
```

2. Configure your TV details in `.env`:
```bash
SAMSUNG_TV_IP=192.168.1.XXX
SAMSUNG_TV_MAC=AA:BB:CC:DD:EE:FF
```

## Usage

### Command Line
```bash
# Turn TV on with art mode
python tv_power.py ON

# Turn TV completely off
python tv_power.py OFF

# With verbose logging
python tv_power.py ON --verbose

# Override IP/MAC from command line
python tv_power.py ON --ip 192.168.1.100 --mac AA:BB:CC:DD:EE:FF
```

### Shell Wrapper
For easier cron usage, use the wrapper script:
```bash
./tv_control.sh ON
./tv_control.sh OFF
```

### Crontab Examples
```bash
# Edit crontab
crontab -e

# Turn on at 8 AM every day
0 8 * * * /path/to/samsung_daily_image/tv_control.sh ON >/dev/null 2>&1

# Turn off at 11 PM every day
0 23 * * * /path/to/samsung_daily_image/tv_control.sh OFF >/dev/null 2>&1

# Turn on at 7 AM on weekdays only
0 7 * * 1-5 /path/to/samsung_daily_image/tv_control.sh ON >/dev/null 2>&1

# Turn off at midnight on weekends
0 0 * * 6,0 /path/to/samsung_daily_image/tv_control.sh OFF >/dev/null 2>&1
```

### Raspberry Pi Systemd Timer (Alternative to Cron)
Create systemd service and timer files for more robust scheduling:

1. Create service file: `/etc/systemd/system/tv-on.service`
```ini
[Unit]
Description=Turn Samsung Frame TV On
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/samsung_daily_image
ExecStart=/home/pi/samsung_daily_image/tv_control.sh ON
StandardOutput=journal
StandardError=journal
```

2. Create timer file: `/etc/systemd/system/tv-on.timer`
```ini
[Unit]
Description=Turn TV on at 8 AM daily
Requires=tv-on.service

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tv-on.timer
sudo systemctl start tv-on.timer
```

## Exit Codes

The script uses specific exit codes for different scenarios:

- `0`: Success - operation completed successfully
- `1`: Invalid arguments - incorrect command line arguments
- `2`: Connection error - could not connect to TV
- `3`: Operation failed - connected but operation failed

## How It Works

### Power ON Sequence:
1. Check if TV is reachable on network
2. If not reachable, send Wake-on-LAN packet (if MAC configured)
3. Wait for TV to boot (up to 30 seconds)
4. Connect to TV via WebSocket API
5. Check current art mode status
6. If not in art mode, enable it
7. Verify operation succeeded

### Power OFF Sequence:
1. Check if TV is reachable
2. If not reachable, assume already off (success)
3. Connect to TV
4. Disable art mode if currently active
5. Send power off command
6. Verify TV is no longer reachable

## Network Requirements

- TV and controlling device must be on same network
- Port 8002 must be accessible (Samsung WebSocket API)
- For Wake-on-LAN:
  - TV must have "Power on with Mobile" enabled in settings
  - Network must support broadcast packets
  - Router must not block MAC broadcasts

## TV Configuration

### Required Settings

On your Samsung Frame TV, configure these settings:

1. **Network > Expert Settings > Power on with Mobile**: ON
   - Required for Wake-on-LAN functionality

2. **General > External Device Manager > Device Connection Manager > Access Notification**:
   - Choose **"Always Allow"** or **"First Time Only"**
   - This prevents repeated authorization popups
   - Without this, you'll get popups every time the script runs

3. **First Run Authorization**:
   - When you first run the script, you'll see a popup on TV: "Allow DailyArtApp to connect?"
   - Select **"Allow"**
   - This authorization is saved if "Access Notification" is set correctly

### Alternative: Simplified Art Mode Control

If you continue getting authorization popups with the main script, use the simplified version:

```bash
python tv_power_simple.py ON   # Enable art mode
python tv_power_simple.py OFF  # Disable art mode (TV stays on)
```

**Simplified version characteristics:**
- Uses only art mode API (no remote control channel)
- No repeated authorization popups
- Cannot send power off signal (only exits art mode)
- Best used with TV's built-in auto-off timer
- Recommended for automated cron jobs if auth issues persist

**To use simplified version in cron:**
```bash
# Turn on and show art at 8 AM
0 8 * * * /path/to/tv_control.sh ON >/dev/null 2>&1

# Configure TV's auto-off timer to turn off at desired time
# Settings > General > Power and Energy Saving > Auto Power Off
```

## Troubleshooting

### Repeated Authorization Popups

**Problem**: TV keeps asking to allow "DailyArtApp" every time script runs

**Solutions**:
1. **Configure TV settings** (recommended):
   - Go to Settings > General > External Device Manager > Device Connection Manager
   - Set "Access Notification" to "Always Allow" or "First Time Only"
   - Accept the authorization popup once

2. **Use simplified script**:
   - Switch to `tv_power_simple.py` which only uses art mode API
   - No remote control channel = no auth popups
   - See "Alternative: Simplified Art Mode Control" section above

3. **Check TV firmware**:
   - Some firmware versions have stricter auth requirements
   - Consider updating TV firmware to latest version

### TV Won't Turn On
- Verify TV IP address is correct: `ping SAMSUNG_TV_IP`
- Check MAC address format: `AA:BB:CC:DD:EE:FF`
- Ensure "Power on with Mobile" is enabled on TV
- Try running with `--verbose` flag for detailed logging

### TV Won't Turn Off
- TV might be in use by another app/source
- Try power button on physical remote first
- Check if TV is already off

### Art Mode Issues
- Ensure TV has at least one artwork uploaded
- TV must be in "TV" or "Art" source (not HDMI input)
- Some firmware versions have art mode API limitations

### Connection Timeouts
- Increase timeout in script (default 30 seconds)
- Check network stability between Pi and TV
- Consider using Ethernet instead of WiFi

## Integration with Daily Art Script

The power control can be integrated with the daily art upload:

```bash
#!/bin/bash
# Daily art with power management

# Turn on TV first
/path/to/tv_control.sh ON

# Wait for TV to fully initialize
sleep 30

# Run daily art upload
/path/to/python /path/to/main.py

# Optional: Turn off after a delay
# sleep 3600  # Display for 1 hour
# /path/to/tv_control.sh OFF
```

## Testing

Test the script manually before adding to cron:

```bash
# Test ON command
python tv_power.py ON --verbose

# Verify TV is on and showing art

# Test OFF command
python tv_power.py OFF --verbose

# Verify TV screen is off
```

## Logging

For production use, redirect output to log files:

```bash
# In crontab with logging
0 8 * * * /path/to/tv_control.sh ON >> /path/to/tv_power.log 2>&1
```

Rotate logs periodically to prevent disk space issues.

## Security Notes

- Store credentials in `.env` file (never commit to git)
- Set appropriate file permissions: `chmod 600 .env`
- Consider network segmentation for IoT devices
- Token files grant TV control access - protect them

## Known Limitations

- Some TV firmware versions may have limited art mode API support
- Wake-on-LAN requires specific TV settings and network configuration
- Power state detection is based on network reachability
- Art mode changes may take a few seconds to apply

## Related Files

- `tv_power.py`: Main power control script
- `tv_control.sh`: Shell wrapper for easier cron usage
- `.env`: Configuration file with TV IP and MAC
- `upload_image.py`: Existing image upload functionality
- `main.py`: Daily art generation and upload