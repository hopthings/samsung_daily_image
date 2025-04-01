#!/usr/bin/env python3
"""Module for uploading images to Samsung Frame TV."""

import os
import sys
import urllib3
from typing import Optional
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS

# Suppress InsecureRequestWarning for local TV connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TVImageUploader:
    """Class to handle image upload and display on Samsung Frame TV."""

    def __init__(self, tv_ip: str = None) -> None:
        """Initialize the uploader with TV IP address.

        Args:
            tv_ip: The IP address of the Samsung TV. If None, it will
                  be loaded from the SAMSUNG_TV_IP environment variable.
        """
        if not tv_ip:
            load_dotenv()
            tv_ip = os.getenv("SAMSUNG_TV_IP")
            if not tv_ip:
                print("Error: SAMSUNG_TV_IP not found in .env file")
                sys.exit(1)

        self.tv_ip = tv_ip
        self.tv = SamsungTVWS(tv_ip, port=8002, name="DailyArtApp")

    def upload_image(self, image_path: str) -> Optional[str]:
        """Upload an image to the TV.

        Args:
            image_path: Path to the image file to upload.

        Returns:
            Content ID if successful, None otherwise.
        """
        if not os.path.exists(image_path):
            print(f"Error: Image {image_path} not found")
            return None

        try:
            # Read the image file as binary data
            with open(image_path, 'rb') as f:
                data = f.read()

            # Determine file type from extension
            file_type = os.path.splitext(image_path)[1][1:].upper()
            if file_type.upper() == 'JPG':
                file_type = 'JPEG'

            # Upload the image with no matte/mount
            # Setting matte to 'none' means no frame/mount
            content_id = self.tv.art().upload(
                data,
                file_type=file_type,
                matte='none',  # No frame/mount
                portrait_matte='none'  # For portrait orientation
            )
            print(f"Uploaded image without matte, content ID: {content_id}")
            return content_id

        except Exception as e:
            print(f"Error uploading image: {e}")
            return None

    def set_active_art(self, content_id: str) -> bool:
        """Set an uploaded image as the active art.

        Args:
            content_id: The content ID of the image to set as active.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Try to ensure TV is in Art Mode
            try:
                self.tv.art().set_artmode(True)
            except Exception:
                # Art mode switching sometimes fails, but we can still
                # set the active image
                pass

            # First remove any matte/mount
            try:
                # Set matte to 'none' to remove any frame/mount
                self.tv.art().change_matte(content_id, matte_id='none')
                print(f"Removed matte for content ID: {content_id}")
            except Exception as e:
                print(f"Note: Could not remove matte: {e}")
                # Continue anyway - not critical

            # Set the image as active
            try:
                self.tv.art().select_image(content_id)
                print(f"Set image with ID: {content_id} as active")
                return True
            except Exception as e:
                print(f"Error setting active image: {e}")

                # Try alternative approach
                try:
                    # Get list of all uploaded images
                    content_list = self.tv.art().get_content_list()
                    # Find matching content ID or use the first one
                    target_id = content_id
                    if content_list and len(content_list) > 0:
                        # Look for our specific content_id first
                        found = False
                        for item in content_list:
                            if item.get("content_id") == content_id:
                                found = True
                                break
                        if not found and len(content_list) > 0:
                            # Use first available if ours not found
                            target_id = content_list[0].get("content_id")

                        # First try to remove matte for the target image
                        try:
                            self.tv.art().change_matte(
                                target_id, matte_id='none'
                            )
                            print(f"Removed matte for alt ID: {target_id}")
                        except Exception:
                            pass  # Continue if this fails

                        # Then set as active
                        self.tv.art().select_image(target_id)
                        print(f"Set alt image ID: {target_id} as active")
                        return True
                except Exception as e2:
                    print(f"Alternative approach failed: {e2}")
                    return False
        except Exception as e:
            print(f"Error setting active art: {e}")
            return False
