#!/usr/bin/env python3
"""Test script to test the select_image method."""

import time
from upload_image import TVImageUploader

def test_select_image():
    """Test if we can set an image as active using our improved method."""
    try:
        print("Creating TV uploader object...")
        uploader = TVImageUploader()
        print("Uploader created successfully")
        
        # Get current image
        try:
            print("\nGetting current art...")
            current = uploader.tv.art().get_current()
            print(f"Current art: {current}")
            
            if current and 'content_id' in current:
                content_id = current['content_id']
                print(f"Current content ID: {content_id}")
                
                # Test our improved set_active_art method
                print("\nTesting improved set_active_art method...")
                success = uploader.set_active_art(content_id)
                print(f"set_active_art result: {success}")
                
                # For comparison, also test direct API call
                print("\nTesting direct API call for comparison...")
                uploader.tv.art().select_image(content_id)
                print("Direct select_image call completed")
                
            else:
                print("No current content ID found")
                
        except Exception as e:
            print(f"Error testing select_image: {e}")
            
    except Exception as e:
        print(f'Connection error: {e}')

if __name__ == "__main__":
    test_select_image()