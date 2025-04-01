#!/usr/bin/env python3
"""Test script to set an uploaded image as active art on Samsung Frame TV."""

import os
import sys
import urllib3
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS
import time

# Suppress InsecureRequestWarning for local TV connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def test_set_active_art() -> bool:
    """Test if we can set an uploaded image as active art."""
    load_dotenv()

    tv_ip = os.getenv("SAMSUNG_TV_IP")
    if not tv_ip:
        print("Error: SAMSUNG_TV_IP not found in .env file")
        sys.exit(1)

    try:
        # Initialize TV
        tv = SamsungTVWS(tv_ip, port=8002, name="DailyArtApp")

        # Ensure TV is in Art Mode
        print("Attempting to switch TV to Art Mode...")
        # Note: The actual method to switch to Art Mode depends on the API
        try:
            # Try to switch to Art Mode - method depends on the API
            if hasattr(tv, 'art') and callable(getattr(tv, 'art', None)):
                try:
                    tv.art().set_artmode(True)
                    print("Switched to Art Mode using set_artmode()")
                except Exception:
                    print("Could not switch to Art Mode with set_artmode()")
            elif hasattr(tv, 'art_mode'):
                tv.art_mode()
                print("Switched to Art Mode")
            else:
                # Alternative approach - try sending key combinations
                print("Art Mode not available, trying alternatives...")
                # Some TVs need KEY_ART key press
                try:
                    tv.send_key("KEY_ART")
                    print("Sent KEY_ART command")
                except Exception:
                    print("Could not send KEY_ART command")

            # Give the TV some time to switch modes
            time.sleep(2)

            # Set our uploaded image as active
            print("Attempting to set uploaded image as active...")
            # Using the art().select() method from the library documentation
            if hasattr(tv, 'art') and callable(getattr(tv, 'art', None)):
                # Use the ID returned from the previous upload
                # Save this ID when uploading images
                image_id = "MY_F0092"  # ID from your upload result

                try:
                    tv.art().select_image(image_id)
                    print(f"Set image with ID: {image_id}")
                    return True
                except Exception as e:
                    print(f"Error setting active image: {e}")

                    # Try alternative methods
                    try:
                        print("Trying alternative method...")
                        # Get list of all uploaded images
                        content_list = tv.art().get_content_list()
                        print(f"Available art: {content_list}")

                        # Find our image in the list or use the first available
                        if content_list and len(content_list) > 0:
                            first_id = content_list[0]["content_id"]
                            tv.art().select_image(first_id)
                            print(f"Set first available image: {first_id}")
                            return True
                    except Exception as e2:
                        print(f"Alternative method failed: {e2}")
                        return False
            else:
                print("Warning: TV API doesn't have art() method")
                # Alternative approach might be needed
                return False

        except AttributeError as e:
            print(f"TV API doesn't support art mode functions directly: {e}")
            return False

    except Exception as e:
        print(f"Error setting active art on TV: {e}")
        return False


if __name__ == "__main__":
    test_set_active_art()
