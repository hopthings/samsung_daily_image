#!/usr/bin/env python3
"""
Debug script for Samsung TV connectivity and state checking.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main() -> None:
    """Main debug function."""
    print("Samsung TV Debug Script")
    print("=" * 50)
    
    load_dotenv()
    tv_ip = os.getenv("SAMSUNG_TV_IP")
    if not tv_ip:
        print("Error: SAMSUNG_TV_IP not found in .env file")
        sys.exit(1)
    
    print(f"TV IP: {tv_ip}")
    
    try:
        from upload_image import TVImageUploader
        
        print("Creating TV uploader...")
        uploader = TVImageUploader(tv_ip)
        
        print("Running comprehensive TV debug state check...")
        uploader.debug_tv_state()
        
        print("\nDebug completed successfully!")
        
    except Exception as e:
        print(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()