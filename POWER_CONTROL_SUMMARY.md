# TV Power Control - Quick Start Guide

## Current Status

✅ **Working**: `tv_power_simple.py` - Art mode control (no authorization issues)
⚠️ **Needs TV Config**: `tv_power.py` - Full power control (requires TV settings change)

## Recommended Approach

### Option 1: Simplified Script (Ready to Use Now)

**Best for**: Quick setup, automated cron jobs, avoiding authorization popups

```bash
python tv_power_simple.py ON   # Enable art mode
python tv_power_simple.py OFF  # Disable art mode
```

**What it does:**
- ✅ Wakes TV with Wake-on-LAN (if configured)
- ✅ Enables/disables art mode
- ✅ No authorization popups
- ❌ Cannot send power off command (only exits art mode)

**Cron setup:**
```bash
# Show art at 8 AM
0 8 * * * cd /Users/MattHopkins/Projects/Python/samsung_daily_image && source .venv/bin/activate && python tv_power_simple.py ON >/dev/null 2>&1

# Let TV auto-off timer handle power off
# Configure on TV: Settings > General > Power and Energy Saving > Auto Power Off
```

### Option 2: Full Power Control (Requires One-Time TV Setup)

**Best for**: Complete power on/off control

1. **Configure TV** (one-time):
   - Settings → General → External Device Manager → Device Connection Manager
   - Set "Access Notification" to **"Always Allow"**
   - Accept authorization for "DailyArtApp" when prompted

2. **Use full script:**
```bash
python tv_power.py ON   # Power on + art mode
python tv_power.py OFF  # Complete power off
```

**What it does:**
- ✅ Full power on/off control
- ✅ Art mode management
- ✅ Wake-on-LAN support
- ⚠️ Requires TV settings configured to avoid auth popups

## Current Configuration

Your `.env` file:
```
SAMSUNG_TV_IP=192.168.105.40
SAMSUNG_TV_MAC=[configured]
```

Both scripts use connection name: `DailyArtApp` (same as your upload_image.py)

## Testing

```bash
# Test simplified version (works now)
python tv_power_simple.py ON
python tv_power_simple.py OFF

# Test full version (after configuring TV settings)
python tv_power.py ON
python tv_power.py OFF
```

## Files Created

- `tv_power.py` - Full power control with remote keys
- `tv_power_simple.py` - Art mode only (no remote keys)
- `tv_control.sh` - Shell wrapper for cron
- `test_tv_power.py` - Interactive test script
- `test_remote_connection.py` - Connection authorization test
- `TV_POWER_CONTROL.md` - Complete documentation

## Recommendation

**For immediate use:** Start with `tv_power_simple.py` since it works now without any TV configuration changes. Combine it with the TV's built-in auto-off timer for complete power management.

**For full control:** Take time to configure the TV settings for "Always Allow", then you can use `tv_power.py` for complete power on/off automation.
