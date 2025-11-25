#!/usr/bin/env python3
"""Test script to verify connection to Samsung Frame TV."""

import os
import sys
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS

def test_connection():
    """Test if we can establish a connection with the TV."""
    load_dotenv()
    
    tv_ip = os.getenv("SAMSUNG_TV_IP")
    if not tv_ip:
        print("Error: SAMSUNG_TV_IP not found in .env file")
        sys.exit(1)
    
    try:
        # Initialize TV with a name for this controller
        tv = SamsungTVWS(tv_ip, port=8002, name="DailyArtApp")
        tv.shortcuts().power()
        
        # Check if the TV is on and accessible
        if tv.rest_device_info():
            print(f"Successfully connected to TV at {tv_ip}")
            return True
        else:
            print(f"TV at {tv_ip} appears to be off or not responding")
            return False
    except Exception as e:
        print(f"Error connecting to TV: {e}")
        return False

if __name__ == "__main__":
    test_connection()