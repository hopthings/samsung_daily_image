# TV Power Control - Quick Reference Card

## ✅ What's Ready to Use

The simplified TV power control is **ready for your Raspberry Pi** with no configuration needed!

## 📋 Copy-Paste Commands for Raspberry Pi

### Step 1: Test the Script

```bash
cd /home/pi/Projects/Python/samsung_daily_image
./tv_power_wrapper.sh ON
```

Expected output: `✓ TV already in art mode` or `✓ Art mode enabled`

### Step 2: Add to Crontab

```bash
crontab -e
```

Then paste this line (wake TV at 8 AM daily):

```
0 8 * * * /home/pi/Projects/Python/samsung_daily_image/tv_power_wrapper.sh ON >> /home/pi/Projects/Python/samsung_daily_image/tv_power.log 2>&1
```

**Remember:** Change `/home/pi/Projects/Python/samsung_daily_image` to your actual path!

### Step 3: Configure TV Auto-Off

On your Samsung Frame TV:
1. Settings → General → Power and Energy Saving → Auto Power Off
2. Set time (e.g., 11:00 PM)

## 🔍 Quick Checks

### View logs
```bash
tail -20 /home/pi/Projects/Python/samsung_daily_image/tv_power.log
```

### List your cron jobs
```bash
crontab -l
```

### Check cron is running
```bash
sudo systemctl status cron
```

## 🎯 What It Does

**At 8 AM every day:**
- ✅ Sends Wake-on-LAN if TV is off
- ✅ Connects to TV
- ✅ Enables art mode
- ✅ Logs result

**At your configured Auto Power Off time:**
- ✅ TV turns off automatically (handled by TV)

## 📁 Files You Have

| File | Purpose |
|------|---------|
| `tv_power_simple.py` | Main script (art mode control) |
| `tv_power_wrapper.sh` | Wrapper for cron jobs |
| `.env` | TV IP and MAC address |
| `tv_power.log` | Cron execution logs |

## ⚡ Quick Troubleshooting

**TV didn't wake up?**
```bash
# Check the log
tail -20 tv_power.log

# Test manually
./tv_power_wrapper.sh ON

# Verify TV settings: Network → Expert Settings → Power on with Mobile: ON
```

**Cron didn't run?**
```bash
# Check if cron scheduled it
crontab -l

# Check system logs
grep CRON /var/log/syslog | tail -20
```

## 🔧 Common Cron Patterns

```bash
# Every day at 8 AM
0 8 * * * /path/to/tv_power_wrapper.sh ON

# Weekdays at 7 AM
0 7 * * 1-5 /path/to/tv_power_wrapper.sh ON

# Weekends at 9 AM
0 9 * * 6,0 /path/to/tv_power_wrapper.sh ON
```

## 📞 Need More Help?

See detailed documentation:
- **RASPBERRY_PI_SETUP.md** - Complete setup guide
- **TV_POWER_CONTROL.md** - Full documentation
- **POWER_CONTROL_SUMMARY.md** - Feature comparison

## ✨ Why This Works

✅ No authorization popups (uses same "DailyArtApp" connection)
✅ No timeout issues (art mode API only)
✅ Wake-on-LAN support (if TV is off)
✅ Simple and reliable
✅ Perfect for automation
