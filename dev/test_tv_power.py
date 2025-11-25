#!/usr/bin/env python3
"""
Test script for TV power control functionality.

This script tests the TV power control in a safe, interactive way.
"""

import os
import sys
import time
import logging
from dotenv import load_dotenv
from tv_power import FrameTVPowerController

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_tv_connection():
    """Test basic TV connectivity."""
    load_dotenv()

    tv_ip = os.getenv('SAMSUNG_TV_IP')
    tv_mac = os.getenv('SAMSUNG_TV_MAC')

    if not tv_ip:
        print("Error: SAMSUNG_TV_IP not found in .env file")
        return False

    print(f"Testing connection to TV at {tv_ip}")
    if tv_mac:
        print(f"MAC address configured: {tv_mac}")
    else:
        print("Warning: No MAC address configured (Wake-on-LAN disabled)")

    controller = FrameTVPowerController(tv_ip, tv_mac)

    # Test reachability
    print("\n1. Testing network reachability...")
    if controller._is_tv_reachable():
        print("   ✓ TV is reachable on network")
    else:
        print("   ✗ TV is not reachable (may be powered off)")
        return False

    # Test connection
    print("\n2. Testing WebSocket connection...")
    if controller._connect_to_tv():
        print("   ✓ Successfully connected to TV")
    else:
        print("   ✗ Failed to connect (may need pairing)")
        return False

    # Test art mode status
    print("\n3. Checking art mode status...")
    art_mode = controller._get_art_mode_status()
    if art_mode is not None:
        status = "enabled" if art_mode else "disabled"
        print(f"   ✓ Art mode is currently {status}")
    else:
        print("   ⚠ Could not determine art mode status")

    return True


def interactive_test():
    """Run an interactive test of power control."""
    print("Samsung Frame TV Power Control - Interactive Test")
    print("=" * 50)

    if not test_tv_connection():
        print("\nConnection test failed. Please check:")
        print("1. TV is powered on")
        print("2. TV IP address is correct in .env")
        print("3. TV and this device are on same network")
        print("4. TV has accepted pairing request")
        return

    print("\n" + "=" * 50)
    print("Connection successful! Ready for power control test.")
    print("\nWARNING: This will actually control your TV!")

    response = input("\nDo you want to test power control? (yes/no): ")
    if response.lower() != 'yes':
        print("Test cancelled.")
        return

    load_dotenv()
    tv_ip = os.getenv('SAMSUNG_TV_IP')
    tv_mac = os.getenv('SAMSUNG_TV_MAC')

    controller = FrameTVPowerController(tv_ip, tv_mac)

    # Test sequence
    tests = [
        ("Turn TV ON with art mode", lambda: controller.turn_on()),
        ("Turn TV OFF", lambda: controller.turn_off()),
    ]

    for test_name, test_func in tests:
        print(f"\n{test_name}")
        response = input("Press Enter to execute (or 'skip' to skip): ")

        if response.lower() == 'skip':
            print("Skipped.")
            continue

        print("Executing...")
        success, message = test_func()

        if success:
            print(f"✓ Success: {message}")
        else:
            print(f"✗ Failed: {message}")

        print("Waiting 5 seconds...")
        time.sleep(5)

    print("\n" + "=" * 50)
    print("Test complete!")

    # Final status check
    print("\nFinal status check...")
    if controller._is_tv_reachable():
        art_mode = controller._get_art_mode_status()
        if art_mode is not None:
            status = "enabled" if art_mode else "disabled"
            print(f"TV is ON, art mode is {status}")
        else:
            print("TV is ON, art mode status unknown")
    else:
        print("TV appears to be OFF")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test TV power control")
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Just test connection without power control'
    )

    args = parser.parse_args()

    if args.quick:
        success = test_tv_connection()
        sys.exit(0 if success else 1)
    else:
        interactive_test()


if __name__ == "__main__":
    main()