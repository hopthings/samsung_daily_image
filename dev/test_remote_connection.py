#!/usr/bin/env python3
"""Test script to establish and authorize TV remote control connection."""

import os
import time
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS

load_dotenv()

tv_ip = os.getenv('SAMSUNG_TV_IP')
print(f"Connecting to TV at {tv_ip}...")
print("\n*** IMPORTANT: Watch your TV screen for an authorization popup! ***")
print("You may need to accept the connection request on the TV.\n")

try:
    # Create connection with a friendly name
    tv = SamsungTVWS(
        tv_ip,
        port=8002,
        name="PowerControl",  # This name will appear on TV
        timeout=60
    )

    print("Connection object created. Attempting to send a test key...")
    print("(Check TV for popup asking to allow 'PowerControl' to connect)")

    # Try to send a simple key that won't do much
    time.sleep(2)
    tv.send_key("KEY_INFO")  # Info button - harmless to press

    print("\n✓ Success! Remote control access is working.")
    print("You can now use tv_power.py to control your TV.")

except Exception as e:
    print(f"\n✗ Failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check if TV is on and network is reachable")
    print("2. Look for authorization popup on TV screen")
    print("3. Check TV Settings → General → External Device Manager")
    print("   → Device Connection Manager → Access Notification")
    print("   Make sure 'First Time Only' or 'Always Allow' is selected")
