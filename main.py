#!/usr/bin/env python3
"""
Samsung Daily Image - Main Application

This application:
1. Generates an art image using DALL-E 3
2. Enhances the image for optimal display on TV
3. Uploads the image to a Samsung Frame TV
4. Sets the image as the active art
"""

import os
import sys
import argparse
import logging
from typing import Optional
from dotenv import load_dotenv

# Import local modules
from generate_image import ImageGenerator
from test_image_enhancement import load_image, save_image, apply_enhancement
from test_enhancement_presets import get_preset_params
# TVImageUploader will be imported after creating the module


class DailyArtApp:
    """Main application for daily art generation and display."""

    def __init__(self, log_level: int = logging.INFO) -> None:
        """Initialize the daily art application.

        Args:
            log_level: The logging level to use.
        """
        # Setup logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("daily_art.log")
            ]
        )
        self.logger = logging.getLogger("DailyArtApp")

        # Load environment variables
        load_dotenv()
        self.tv_ip = os.getenv("SAMSUNG_TV_IP")
        if not self.tv_ip:
            self.logger.error("SAMSUNG_TV_IP not found in .env file")
            sys.exit(1)

        # Initialize components
        self.image_generator = ImageGenerator()
        # TVImageUploader will be initialized in run()
        
        # Create enhanced images directory if it doesn't exist
        self.enhanced_dir = "enhanced_images"
        os.makedirs(self.enhanced_dir, exist_ok=True)

    def enhance_image(self, image_path: str, preset: str = "upscale-sharp") -> Optional[str]:
        """Enhance an image using the specified preset.
        
        Args:
            image_path: Path to the image to enhance
            preset: Name of the enhancement preset to use
            
        Returns:
            Path to the enhanced image if successful, None otherwise
        """
        try:
            # Get preset parameters
            presets = get_preset_params()
            if preset not in presets:
                self.logger.error(f"Unknown preset: {preset}")
                self.logger.info(f"Available presets: {', '.join(presets.keys())}")
                return None
            
            params = presets[preset]
            
            # Load the image
            image = load_image(image_path)
            if not image:
                self.logger.error(f"Failed to load image: {image_path}")
                return None
            
            # Apply enhancement
            self.logger.info(f"Enhancing image with preset: {preset}")
            orig_width, orig_height = image.size
            self.logger.info(f"Original size: {orig_width}x{orig_height}")
            
            enhanced = apply_enhancement(image, **params)
            
            # Create output path
            base_name = os.path.basename(image_path)
            name_root, ext = os.path.splitext(base_name)
            output_filename = f"{name_root}_{preset}{ext}"
            output_path = os.path.join(self.enhanced_dir, output_filename)
            
            # Save the enhanced image
            if save_image(enhanced, output_path):
                new_width, new_height = enhanced.size
                self.logger.info(f"Enhanced size: {new_width}x{new_height}")
                self.logger.info(f"Enhanced image saved to: {output_path}")
                return output_path
            
            return None
            
        except Exception as e:
            self.logger.exception(f"Error enhancing image: {e}")
            return None

    def run(self, custom_prompt: Optional[str] = None,
            custom_image: Optional[str] = None,
            enhancement_preset: Optional[str] = "upscale-sharp",
            skip_upload: bool = False) -> bool:
        """Run the main application flow.

        Args:
            custom_prompt: Optional custom prompt for image generation.
            custom_image: Optional path to existing image to use instead of
                         generating a new one.
            enhancement_preset: Preset to use for image enhancement.
            skip_upload: If True, skip uploading to TV.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Import here to avoid circular imports
            from upload_image import TVImageUploader
            
            # Initialize TV uploader if needed
            tv_uploader = None if skip_upload else TVImageUploader(self.tv_ip)
            
            # Step 1: Get or generate an image
            if custom_image and os.path.exists(custom_image):
                self.logger.info(f"Using provided image: {custom_image}")
                image_path = custom_image
            else:
                self.logger.info("Generating new art image...")
                image_path = self.image_generator.generate_image(custom_prompt)
                if not image_path:
                    self.logger.error("Failed to generate image")
                    return False
                self.logger.info(f"Image generated: {image_path}")

            # Step 2: Enhance the image
            if enhancement_preset:
                self.logger.info(f"Enhancing image with preset: {enhancement_preset}")
                enhanced_path = self.enhance_image(image_path, enhancement_preset)
                if enhanced_path:
                    self.logger.info(f"Image enhanced: {enhanced_path}")
                    # Use the enhanced image for upload
                    image_path = enhanced_path
                else:
                    self.logger.warning("Failed to enhance image, using original")

            # Skip uploading if requested
            if skip_upload:
                self.logger.info("Skipping upload to TV as requested")
                return True

            # Step 3: Upload image to TV
            self.logger.info(f"Uploading image to TV at {self.tv_ip}...")
            content_id = tv_uploader.upload_image(image_path)
            if not content_id:
                self.logger.error("Failed to upload image to TV")
                return False
            self.logger.info(f"Image uploaded successfully. ID: {content_id}")

            # Step 4: Set as active art
            self.logger.info("Setting image as active art...")
            if not tv_uploader.set_active_art(content_id):
                self.logger.error("Failed to set image as active art")
                return False
            self.logger.info("Image successfully set as active art")

            return True

        except Exception as e:
            self.logger.exception(f"Error in application flow: {e}")
            return False


def create_upload_module() -> None:
    """Create the upload_image.py module if it doesn't exist."""
    if os.path.exists("upload_image.py"):
        return

    upload_module_content = """#!/usr/bin/env python3
\"\"\"Module for uploading images to Samsung Frame TV.\"\"\"

import os
import sys
import urllib3
from typing import Optional
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS
import time

# Suppress InsecureRequestWarning for local TV connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TVImageUploader:
    \"\"\"Class to handle image upload and display on Samsung Frame TV.\"\"\"

    def __init__(self, tv_ip: str = None) -> None:
        \"\"\"Initialize the uploader with TV IP address.

        Args:
            tv_ip: The IP address of the Samsung TV. If None, it will
                  be loaded from the SAMSUNG_TV_IP environment variable.
        \"\"\"
        if not tv_ip:
            load_dotenv()
            tv_ip = os.getenv("SAMSUNG_TV_IP")
            if not tv_ip:
                print("Error: SAMSUNG_TV_IP not found in .env file")
                sys.exit(1)

        self.tv_ip = tv_ip
        self.tv = SamsungTVWS(tv_ip, port=8002, name="DailyArtApp")

    def upload_image(self, image_path: str) -> Optional[str]:
        \"\"\"Upload an image to the TV.

        Args:
            image_path: Path to the image file to upload.

        Returns:
            Content ID if successful, None otherwise.
        \"\"\"
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

            # Upload the image
            content_id = self.tv.art().upload(data, file_type=file_type)
            return content_id

        except Exception as e:
            print(f"Error uploading image: {e}")
            return None

    def set_active_art(self, content_id: str) -> bool:
        \"\"\"Set an uploaded image as the active art.

        Args:
            content_id: The content ID of the image to set as active.

        Returns:
            True if successful, False otherwise.
        \"\"\"
        try:
            # Try to ensure TV is in Art Mode
            try:
                self.tv.art().set_artmode(True)
            except Exception:
                # Art mode switching sometimes fails, but we can still
                # set the active image
                pass

            # Set the image as active
            try:
                self.tv.art().select_image(content_id)
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
                        self.tv.art().select_image(target_id)
                        return True
                except Exception as e2:
                    print(f"Alternative approach failed: {e2}")
                    return False
        except Exception as e:
            print(f"Error setting active art: {e}")
            return False
"""

    with open("upload_image.py", "w") as f:
        f.write(upload_module_content)


def main() -> None:
    """Main function to parse arguments and run the application."""
    parser = argparse.ArgumentParser(
        description="Samsung Daily Image - Generate and display art"
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Custom prompt for image generation."
    )
    parser.add_argument(
        "--image", "-i",
        help="Path to existing image file to upload instead of generating one."
    )
    parser.add_argument(
        "--enhance", "-e",
        default="upscale-sharp",
        help="Enhancement preset to use (default: 'upscale-sharp'). "
             "Use 'none' to skip enhancement."
    )
    parser.add_argument(
        "--list-presets", "-l",
        action="store_true",
        help="List available enhancement presets and exit."
    )
    parser.add_argument(
        "--skip-upload", "-s",
        action="store_true",
        help="Skip uploading to TV - useful for testing."
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging."
    )

    args = parser.parse_args()
    
    # List available presets if requested
    if args.list_presets:
        presets = get_preset_params()
        print("Available enhancement presets:")
        for name, params in presets.items():
            print(f"  {name}")
        sys.exit(0)
    
    # Ensure required modules exist
    create_upload_module()

    # Run application
    log_level = logging.DEBUG if args.debug else logging.INFO
    app = DailyArtApp(log_level=log_level)
    
    # Determine enhancement preset
    enhancement_preset = None if args.enhance.lower() == "none" else args.enhance
    
    success = app.run(
        args.prompt, 
        args.image, 
        enhancement_preset,
        args.skip_upload
    )

    if success:
        print("Daily art successfully generated and enhanced!")
        if not args.skip_upload:
            print("Image was uploaded and set as active art on TV")
    else:
        print("Failed to complete daily art process")
        sys.exit(1)


if __name__ == "__main__":
    main()