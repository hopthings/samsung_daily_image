# Raspberry Pi Cron Setup Guide

## Quick Setup

### 1. Test the Wrapper Script

First, make sure everything works manually:

```bash
cd /home/pi/Projects/Python/samsung_daily_image  # Adjust path as needed

# Test ON command
./tv_power_wrapper.sh ON

# Check the TV - it should wake up and show art mode
```

### 2. Set Up Cron Job

Edit your crontab:

```bash
crontab -e
```

Add this line to turn on the TV at 8 AM every day:

```bash
# Turn on Samsung Frame TV and enable art mode at 8 AM daily
0 8 * * * /home/pi/Projects/Python/samsung_daily_image/tv_power_wrapper.sh ON >> /home/pi/Projects/Python/samsung_daily_image/tv_power.log 2>&1
```

**Note:** Adjust the path `/home/pi/Projects/Python/samsung_daily_image` to match your actual installation directory.

### 3. Configure TV Auto-Off Timer

Since the simplified script can't send power-off commands, use the TV's built-in timer:

1. On your Samsung Frame TV, go to:
   - **Settings** → **General** → **Power and Energy Saving** → **Auto Power Off**
2. Set your desired off time (e.g., 11 PM)

## Alternative: Use TV's Off Timer Feature

For more flexible daily schedules, use the TV's Off Timer instead of Auto Power Off:

1. **Settings** → **General** → **System Manager** → **Time** → **Off Timer**
2. Set specific times for TV to turn off

## Complete Daily Art Workflow

If you want to combine TV power control with your daily art upload:

```bash
crontab -e
```

Add these lines:

```bash
# Wake TV and show art at 8 AM
0 8 * * * /home/pi/Projects/Python/samsung_daily_image/tv_power_wrapper.sh ON >> /home/pi/Projects/Python/samsung_daily_image/tv_power.log 2>&1

# Run daily art upload at 8:05 AM (after TV is awake)
5 8 * * * /home/pi/Projects/Python/samsung_daily_image/run_daily_image.sh >> /home/pi/Projects/Python/samsung_daily_image/daily_art.log 2>&1
```

## Cron Schedule Examples

```bash
# Every day at 8 AM
0 8 * * * /path/to/tv_power_wrapper.sh ON

# Weekdays only at 7 AM
0 7 * * 1-5 /path/to/tv_power_wrapper.sh ON

# Weekend mornings at 9 AM
0 9 * * 6,0 /path/to/tv_power_wrapper.sh ON

# Multiple times per day
0 8 * * * /path/to/tv_power_wrapper.sh ON    # Morning
0 18 * * * /path/to/tv_power_wrapper.sh ON   # Evening
```

## Viewing Logs

Check if the cron job is working:

```bash
# View recent log entries
tail -20 /home/pi/Projects/Python/samsung_daily_image/tv_power.log

# Watch logs in real-time
tail -f /home/pi/Projects/Python/samsung_daily_image/tv_power.log

# View all cron execution logs
grep CRON /var/log/syslog | tail -20
```

## Troubleshooting

### Cron job not running

1. **Check cron is running:**
   ```bash
   sudo systemctl status cron
   ```

2. **Check your crontab:**
   ```bash
   crontab -l
   ```

3. **Check system logs:**
   ```bash
   grep CRON /var/log/syslog | tail -50
   ```

### Script runs but TV doesn't turn on

1. **Check the log file:**
   ```bash
   cat /home/pi/Projects/Python/samsung_daily_image/tv_power.log
   ```

2. **Test manually:**
   ```bash
   cd /home/pi/Projects/Python/samsung_daily_image
   ./tv_power_wrapper.sh ON
   ```

3. **Verify .env file exists:**
   ```bash
   ls -la /home/pi/Projects/Python/samsung_daily_image/.env
   cat /home/pi/Projects/Python/samsung_daily_image/.env
   ```

4. **Check Wake-on-LAN is configured:**
   - TV Setting: Network → Expert Settings → Power on with Mobile: **ON**
   - Verify `SAMSUNG_TV_MAC` is set in `.env`

### Virtual environment issues

If you get "Virtual environment not found" errors:

```bash
cd /home/pi/Projects/Python/samsung_daily_image
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Testing Before Production

Test your cron setup with a near-future time:

1. Edit crontab:
   ```bash
   crontab -e
   ```

2. Add a test entry (adjust time to 2 minutes from now):
   ```bash
   # Test at 13:47 (1:47 PM)
   47 13 * * * /home/pi/Projects/Python/samsung_daily_image/tv_power_wrapper.sh ON >> /home/pi/Projects/Python/samsung_daily_image/tv_power.log 2>&1
   ```

3. Wait for the scheduled time and check:
   ```bash
   tail -20 /home/pi/Projects/Python/samsung_daily_image/tv_power.log
   ```

4. If successful, remove test entry and add your real schedule

## Files Overview

- **tv_power_simple.py** - Main power control script (art mode only)
- **tv_power_wrapper.sh** - Wrapper for cron (this is what you schedule)
- **tv_power.log** - Log file for cron executions
- **.env** - Configuration (TV IP and MAC address)

## Expected Behavior

When the cron job runs at 8 AM:

1. ✅ Script activates virtual environment
2. ✅ If TV is off, sends Wake-on-LAN packet
3. ✅ Waits for TV to boot (up to 10 seconds)
4. ✅ Connects to TV API
5. ✅ Enables art mode
6. ✅ TV displays artwork
7. ✅ Logs success to tv_power.log

At configured Auto Power Off time (e.g., 11 PM):

1. ✅ TV turns off automatically
2. ✅ Screen goes black

## Benefits of This Approach

✅ **No authorization popups** - Uses art mode API only
✅ **Reliable** - No WebSocket timeout issues
✅ **Simple** - Works with TV's built-in timer for power off
✅ **Automated** - Set it and forget it
✅ **Logged** - Easy to troubleshoot with log files

## Advanced: Systemd Timer (Alternative to Cron)

For more robust scheduling, use systemd timers instead of cron:

### Create service file
```bash
sudo nano /etc/systemd/system/tv-on.service
```

Content:
```ini
[Unit]
Description=Turn Samsung Frame TV On
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/Projects/Python/samsung_daily_image
ExecStart=/home/pi/Projects/Python/samsung_daily_image/tv_power_wrapper.sh ON
StandardOutput=append:/home/pi/Projects/Python/samsung_daily_image/tv_power.log
StandardError=append:/home/pi/Projects/Python/samsung_daily_image/tv_power.log
```

### Create timer file
```bash
sudo nano /etc/systemd/system/tv-on.timer
```

Content:
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

### Enable and start
```bash
sudo systemctl daemon-reload
sudo systemctl enable tv-on.timer
sudo systemctl start tv-on.timer

# Check status
sudo systemctl status tv-on.timer
sudo systemctl list-timers
```

## Questions?

If you encounter issues, check:

1. Log file: `/home/pi/Projects/Python/samsung_daily_image/tv_power.log`
2. System logs: `/var/log/syslog`
3. Network connectivity: `ping <SAMSUNG_TV_IP>`
4. TV settings: Wake-on-LAN enabled
