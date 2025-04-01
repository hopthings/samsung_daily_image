#!/usr/bin/env python3
"""Test script to upload an image to Samsung Frame TV."""

import os
import sys
import urllib3
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS
import requests
from PIL import Image
from io import BytesIO
from typing import Optional

# Suppress InsecureRequestWarning for local TV connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def download_sample_image() -> Optional[str]:
    """Download a sample 16:9 image for testing."""
    # Using an abstract art image from Unsplash with 16:9 ratio
    url = "https://source.unsplash.com/random/1920x1080/?abstract,painting"
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Save the image locally
        img = Image.open(BytesIO(response.content))
        os.makedirs("images", exist_ok=True)
        image_path = "images/sample_test.jpg"
        img.save(image_path, format="JPEG")
        print(f"Downloaded sample image to {image_path}")
        return image_path
    except Exception as e:
        print(f"Error downloading sample image: {e}")
        return None


def test_upload_image() -> bool:
    """Test if we can upload an image to the TV."""
    load_dotenv()

    tv_ip = os.getenv("SAMSUNG_TV_IP")
    if not tv_ip:
        print("Error: SAMSUNG_TV_IP not found in .env file")
        sys.exit(1)

    # Use the local sample image instead of downloading
    # Samsung Frame TV supports both JPG and PNG formats
    image_path = "sample_image.jpeg"
    if not os.path.exists(image_path):
        print(f"Error: Sample image {image_path} not found")
        sys.exit(1)

    try:
        # Initialize TV
        tv = SamsungTVWS(tv_ip, port=8002, name="DailyArtApp")

        # Upload the image - implementation depends on the API's capabilities
        # This is a placeholder - adapt based on the actual API methods
        print(f"Attempting to upload image {image_path}")
        print(f"To TV at {tv_ip}")

        # Using the art().upload() method from the library documentation
        try:
            # Read the image file as binary data
            with open(image_path, 'rb') as f:
                data = f.read()

            # Call the art().upload method with appropriate file type
            if hasattr(tv, 'art') and callable(getattr(tv, 'art', None)):
                is_jpeg = image_path.lower().endswith(('.jpg', '.jpeg'))
                file_type = 'JPEG' if is_jpeg else 'PNG'
                result = tv.art().upload(data, file_type=file_type)
                print(f"Upload result: {result}")
                return True
            else:
                print("Warning: TV API doesn't have art() method")
                # Alternative approach might be needed
                return False
        except Exception as e:
            print(f"Error trying to upload image: {e}")
            return False

    except Exception as e:
        print(f"Error uploading image to TV: {e}")
        return False


if __name__ == "__main__":
    test_upload_image()
