#!/usr/bin/env python3
"""Test script to explore the art module methods."""

import time
import inspect
from upload_image import TVImageUploader

def test_art_methods():
    """Test what methods are available in the art module."""
    try:
        print("Creating TV uploader object...")
        uploader = TVImageUploader()
        print("Uploader created successfully")
        
        time.sleep(2)
        
        # Get the art module
        art_module = uploader.tv.art()
        print(f"Art module type: {type(art_module)}")
        
        # List all available methods in the art module
        print("\nAvailable methods in art module:")
        for method_name in dir(art_module):
            if not method_name.startswith('_'):  # Skip private methods
                method = getattr(art_module, method_name)
                if callable(method):
                    try:
                        signature = str(inspect.signature(method))
                        print(f"- {method_name}{signature}")
                    except:
                        print(f"- {method_name}(...)")
        
        # Try to get art list
        try:
            print("\nTrying to list artwork...")
            if hasattr(art_module, 'get_list'):
                items = art_module.get_list()
                print(f"Found {len(items)} items using get_list()")
            elif hasattr(art_module, 'get_content_list'):
                items = art_module.get_content_list()
                print(f"Found {len(items)} items using get_content_list()")
            else:
                print("No list method found")
        except Exception as e:
            print(f"Error listing artwork: {e}")
            
    except Exception as e:
        print(f'Connection error: {e}')

if __name__ == "__main__":
    test_art_methods()