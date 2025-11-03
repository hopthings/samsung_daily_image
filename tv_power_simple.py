#!/usr/bin/env python3
"""
Simplified Samsung Frame TV Power Control using Art Mode API only.

This version only uses the art mode API which doesn't require repeated
authorization popups. It's simpler but has limitations:
- ON: Ensures TV is reachable and attempts to enable art mode
- OFF: Can't truly power off, but can exit art mode

For true power off, you'll need to use the TV's auto-off timer settings.

Usage:
    python tv_power_simple.py ON    # Enable art mode
    python tv_power_simple.py OFF   # Exit art mode (TV stays on)
"""

import os
import sys
import time
import urllib3
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Optional Wake-on-LAN
try:
    from wakeonlan import send_magic_packet
    HAS_WOL = True
except ImportError:
    HAS_WOL = False


def wake_tv(mac_address: str) -> bool:
    """Send Wake-on-LAN packet to TV."""
    if not HAS_WOL or not mac_address:
        return False
    try:
        send_magic_packet(mac_address)
        return True
    except Exception as e:
        print(f"WOL failed: {e}")
        return False


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1].upper() not in ['ON', 'OFF']:
        print("Usage: tv_power_simple.py [ON|OFF]")
        return 1

    command = sys.argv[1].upper()
    load_dotenv()

    tv_ip = os.getenv('SAMSUNG_TV_IP')
    tv_mac = os.getenv('SAMSUNG_TV_MAC')

    if not tv_ip:
        print("Error: SAMSUNG_TV_IP not set in .env")
        return 1

    try:
        # If turning on and TV not reachable, try WOL
        if command == 'ON':
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((tv_ip, 8002))
                sock.close()

                if result != 0 and tv_mac:
                    print(f"TV not reachable, sending Wake-on-LAN to {tv_mac}...")
                    wake_tv(tv_mac)
                    print("Waiting 10 seconds for TV to boot...")
                    time.sleep(10)
            except Exception:
                pass

        # Connect to TV
        print(f"Connecting to TV at {tv_ip}...")
        tv = SamsungTVWS(tv_ip, port=8002, name="DailyArtApp", timeout=60)

        if command == 'ON':
            print("Enabling art mode...")
            try:
                tv.art().set_artmode(True)
                print("✓ Art mode enabled")
                return 0
            except Exception as e:
                error_str = str(e)
                if "error number -7" in error_str:
                    print("✓ TV already in art mode")
                    return 0
                raise

        else:  # OFF
            print("Disabling art mode...")
            try:
                tv.art().set_artmode(False)
                print("✓ Art mode disabled (TV remains on)")
                print("Note: Use TV's auto-off timer for complete power off")
                return 0
            except Exception as e:
                error_str = str(e)
                if "error number -7" in error_str:
                    print("✓ TV already in normal mode")
                    return 0
                raise

    except Exception as e:
        print(f"✗ Error: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
