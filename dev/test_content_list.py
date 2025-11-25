#!/usr/bin/env python3
"""Test script to check the content list on the TV."""

import time
from upload_image import TVImageUploader

def test_content_list():
    """Test if we can retrieve the content list from the TV."""
    try:
        print("Creating TV uploader object...")
        uploader = TVImageUploader()
        print("Uploader created successfully")
        
        time.sleep(2)
        
        print("Testing content list retrieval...")
        try:
            content_list = uploader.tv.art().get_content_list()
            print(f'Found {len(content_list)} items')
            print('First few items:')
            for item in content_list[:3]:
                print(f'- {item.get("content_id", "unknown")}')
        except Exception as e:
            print(f'Error retrieving content list: {e}')
            
    except Exception as e:
        print(f'Connection error: {e}')

if __name__ == "__main__":
    test_content_list()