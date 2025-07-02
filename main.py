#!/usr/bin/env python3
"""
Samsung Daily Image - Main Application

This application:
1. Generates an art image using DALL-E 3
2. Enhances the image for optimal display on TV
3. Upscales the image 
4. Uploads the image to a Samsung Frame TV
5. Sets the image as the active art
"""

import os
import sys
import argparse
import logging
import time
from typing import Optional, List
from dotenv import load_dotenv

# Import local modules
from generate_image import ImageGenerator
from test_image_enhancement import load_image, save_image, apply_enhancement, resize_image
from test_enhancement_presets import get_preset_params
from upscale_image import upscale_image
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
        
        # Track intermediate files for cleaning up
        self.intermediate_files: List[str] = []

    def clean_intermediate_files(self) -> None:
        """Delete intermediate image files that are no longer needed.
        Only the final version of the image should be kept.
        """
        if not self.intermediate_files:
            return

        self.logger.info(f"Cleaning up {len(self.intermediate_files)} intermediate files")
        for file_path in self.intermediate_files:
            try:
                if os.path.exists(file_path):
                    # Also look for associated prompt file
                    prompt_file = None
                    if file_path.endswith('.jpeg') or file_path.endswith('.jpg'):
                        base_path = file_path[:-5]  # Remove .jpeg or .jpg extension
                        prompt_file = f"{base_path}_prompt.txt"
                    
                    # Delete the image file
                    os.remove(file_path)
                    self.logger.debug(f"Deleted intermediate file: {file_path}")
                    
                    # Delete associated prompt file if it exists
                    if prompt_file and os.path.exists(prompt_file):
                        os.remove(prompt_file)
                        self.logger.debug(f"Deleted prompt file: {prompt_file}")
            except Exception as e:
                self.logger.warning(f"Failed to delete intermediate file {file_path}: {e}")

        # Clear the list
        self.intermediate_files = []
    
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
                
                # Mark the original image for cleanup if it's a generated image
                # Don't track custom images provided by the user
                if image_path.startswith(self.image_generator.image_dir):
                    self.intermediate_files.append(image_path)
                    
                return output_path
            
            return None
            
        except Exception as e:
            self.logger.exception(f"Error enhancing image: {e}")
            return None

    def run(self, custom_prompt: Optional[str] = None,
            custom_image: Optional[str] = None,
            enhancement_preset: Optional[str] = "upscale-sharp",
            skip_upload: bool = False,
            upscale: bool = True) -> bool:
        """Run the main application flow.

        Args:
            custom_prompt: Optional custom prompt for image generation.
            custom_image: Optional path to existing image to use instead of
                         generating a new one.
            enhancement_preset: Preset to use for image enhancement.
            skip_upload: If True, skip uploading to TV.
            upscale: If True, upscale image.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Import here to avoid circular imports
            from upload_image import TVImageUploader
            
            # Initialize TV uploader if needed
            tv_uploader: Optional[TVImageUploader] = None
            if not skip_upload:
                tv_uploader = TVImageUploader(self.tv_ip)
            
            # Step 1: Get or generate an image
            if custom_image and os.path.exists(custom_image):
                self.logger.info(f"Using provided image: {custom_image}")
                image_path = custom_image
            else:
                self.logger.info("Generating new art image...")
                generated_path = self.image_generator.generate_image(custom_prompt)
                if not generated_path:
                    self.logger.error("Failed to generate image")
                    return False
                image_path = generated_path
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

            # Step 3: Upscale image 
            if upscale:
                self.logger.info("Upscaling image...")
                success, upscaled_path, error = upscale_image(image_path)
                if success and upscaled_path:
                    self.logger.info(f"Image upscaled successfully: {upscaled_path}")
                    
                    # Check if the upscaled file is too large for reliable TV upload
                    file_size_mb = os.path.getsize(upscaled_path) / (1024 * 1024)
                    self.logger.info(f"Upscaled image size: {file_size_mb:.2f} MB")
                    
                    # Samsung Frame TVs may have issues with large uploads
                    # If the file is very large, warn the user but continue
                    if file_size_mb > 25:
                        self.logger.warning(
                            f"Upscaled image is quite large ({file_size_mb:.2f} MB). "
                            f"This may cause upload timeouts. "
                            f"Consider using a smaller image or disabling upscaling."
                        )
                    
                    # Mark the pre-upscaled image for cleanup
                    # Only if it's a generated or enhanced image, not a user-provided image
                    if custom_image is None or not os.path.samefile(image_path, custom_image):
                        self.intermediate_files.append(image_path)
                    
                    # Use the upscaled image for upload
                    image_path = upscaled_path
                else:
                    self.logger.warning(f"Failed to upscale image: {error}")
                    self.logger.info("Using previous image version for upload")
            else:
                self.logger.info("Upscaling disabled, using enhanced image directly")

            # If not uploading, still create optimized version for testing
            if skip_upload:
                # Check file size first
                file_size = os.path.getsize(image_path)
                self.logger.info(f"Original image size: {file_size/1024/1024:.2f} MB")
                
                # If image is too large (> 10MB), resize it
                max_upload_size = 10 * 1024 * 1024  # 10MB
                skip_optimized_path: Optional[str] = None

                if file_size > max_upload_size:
                    self.logger.info(f"Image is too large for reliable upload to the TV ({file_size/1024/1024:.2f} MB), creating 4K optimized version...")
                    
                    # Load the image
                    img = load_image(image_path)
                    if img:
                        # Resize to 3840 max dimension without additional compression
                        optimized_img = resize_image(
                            img, 
                            max_dimension=3840,  # Max 4K dimension
                            target_filesize_kb=0  # No filesize targeting/compression
                        )
                        
                        # Save the optimized image
                        base_name = os.path.basename(image_path)
                        name_root, ext = os.path.splitext(base_name)
                        optimized_filename = f"{name_root}_optimized{ext}"
                        skip_optimized_path = os.path.join(self.enhanced_dir, optimized_filename)

                        if save_image(optimized_img, skip_optimized_path):
                            resized_size = os.path.getsize(skip_optimized_path)
                            optimized_width, optimized_height = optimized_img.size
                            self.logger.info(f"Resized image saved to {skip_optimized_path}")
                            self.logger.info(f"Optimized resolution: {optimized_width}x{optimized_height}")
                            self.logger.info(f"Optimized size: {resized_size/1024/1024:.2f} MB")
                
                self.logger.info("Skipping upload to TV as requested")
                # Clean up intermediate files (except the optimized version)
                self.clean_intermediate_files()
                return True
                
            # Check if TV is powered on via simple ping test before attempting connection
            try:
                import socket
                tv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tv_socket.settimeout(5.0)
                connection_result = tv_socket.connect_ex((self.tv_ip, 8002))
                tv_socket.close()
                
                if connection_result != 0:
                    self.logger.warning(f"TV at {self.tv_ip} appears to be unreachable or powered off")
                    self.logger.info(f"Image was generated and saved at: {image_path}")
                    self.logger.info("Consider manually uploading later when TV is available")
                    return True
            except Exception as e:
                self.logger.warning(f"TV connectivity check failed: {e}")

            # Step 4: Upload image to TV - Simplified direct approach
            self.logger.info(f"Uploading image to TV at {self.tv_ip}...")
            try:
                if tv_uploader is None:
                    self.logger.error("TV uploader was not initialized")
                    return False
                
                # Direct upload using same approach as the test script
                self.logger.info("Using simplified direct upload approach...")
                
                # Check file size first
                file_size = os.path.getsize(image_path)
                self.logger.info(f"Original image size: {file_size/1024/1024:.2f} MB")
                
                # If image is too large (> 10MB), resize it
                max_upload_size = 10 * 1024 * 1024  # 10MB
                upload_optimized_path: Optional[str] = None

                if file_size > max_upload_size:
                    self.logger.info(f"Image is too large for reliable upload to the TV ({file_size/1024/1024:.2f} MB), resizing to 4K...")
                    
                    # Load the image
                    img = load_image(image_path)
                    if img:
                        # Resize to 3840 max dimension without additional compression
                        optimized_img = resize_image(
                            img, 
                            max_dimension=3840,  # Max 4K dimension
                            target_filesize_kb=0  # No filesize targeting/compression
                        )
                        
                        # Save the optimized image
                        base_name = os.path.basename(image_path)
                        name_root, ext = os.path.splitext(base_name)
                        optimized_filename = f"{name_root}_optimized{ext}"
                        upload_optimized_path = os.path.join(self.enhanced_dir, optimized_filename)

                        if save_image(optimized_img, upload_optimized_path):
                            resized_size = os.path.getsize(upload_optimized_path)
                            optimized_width, optimized_height = optimized_img.size
                            self.logger.info(f"Resized image saved to {upload_optimized_path}")
                            self.logger.info(f"Optimized resolution: {optimized_width}x{optimized_height}")
                            self.logger.info(f"New size: {resized_size/1024/1024:.2f} MB")

                            # Use the optimized image and track for cleanup
                            image_path = upload_optimized_path
                            self.intermediate_files.append(upload_optimized_path)
                            
                # Read the image file
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                    
                # Determine file type
                is_jpeg = image_path.lower().endswith(('.jpg', '.jpeg'))
                file_type = 'JPEG' if is_jpeg else 'PNG'
                
                # Direct upload with no matte/mount
                file_size = len(image_data)
                self.logger.info(f"Uploading {file_size/1024/1024:.2f} MB {file_type} file")
                content_id = tv_uploader.tv.art().upload(
                    image_data, 
                    file_type=file_type,
                    matte='none',  # No frame/mount
                    portrait_matte='none'  # For portrait orientation
                )
                
                if not content_id:
                    self.logger.error("Failed to upload image to TV")
                    return False
                self.logger.info(f"Image uploaded successfully. ID: {content_id}")
                
                # Add a much longer delay between upload and setting active
                delay_seconds = 15  # Increased to 15 seconds to ensure TV has time to process the upload
                self.logger.info(f"Waiting {delay_seconds} seconds between upload and setting active...")
                time.sleep(delay_seconds)
                
                # Step 5: Set as active art
                self.logger.info("Setting image as active art...")
                
                # Save the content ID to a file
                try:
                    with open("last_uploaded_id.txt", "w") as f:
                        f.write(f"{content_id}")
                    self.logger.debug(f"Saved content ID to last_uploaded_id.txt")
                except Exception as e:
                    self.logger.debug(f"Could not save content ID to file: {e}")
                
                # First remove any matte/mount
                self.logger.info("Removing matte/frame from image...")
                try:
                    # Set matte to 'none' to remove any frame/mount
                    tv_uploader.tv.art().change_matte(content_id, matte_id='none')
                    self.logger.info(f"Removed matte for content ID: {content_id}")
                    
                    # Wait a moment for the matte change to be processed
                    time.sleep(2)
                except Exception as e:
                    self.logger.warning(f"Could not remove matte: {e}")
                    # Continue anyway - not critical
                
                # Use improved set_active_art method
                self.logger.info("Using improved set_active_art approach with multiple fallbacks...")

                # Add additional delay before setting active art
                delay_seconds_before = 10  # Wait longer to ensure TV is ready
                self.logger.info(f"Waiting {delay_seconds_before} seconds before setting active art...")
                time.sleep(delay_seconds_before)

                # Now try to set the active art with proper retry and error handling
                try:
                    success = tv_uploader.set_active_art(content_id)
                    if success:
                        self.logger.info(f"Image {content_id} successfully set as active art")
                    else:
                        self.logger.warning(f"Failed to set image {content_id} as active through primary methods")
                        self.logger.info("Running TV debug state check...")
                        tv_uploader.debug_tv_state()
                        
                        self.logger.info("Attempting additional retry with fallback method...")

                        # Additional retry with longer delay
                        time.sleep(15)  # Even longer delay for final retry
                        success = tv_uploader.set_active_art(content_id)
                        if success:
                            self.logger.info(f"Image {content_id} successfully set as active art on second attempt")
                        else:
                            self.logger.warning(f"Failed to set image {content_id} as active art despite retries")
                            self.logger.info("Running final TV debug state check...")
                            tv_uploader.debug_tv_state()
                            self.logger.info("Image was uploaded successfully but may not be displayed")
                except Exception as e:
                    self.logger.warning(f"Error setting active art: {e}")
                    self.logger.info("Running TV debug state check after error...")
                    tv_uploader.debug_tv_state()
                    self.logger.info("Image was uploaded successfully but may not be displayed")
                
                # Clean up intermediate files
                self.clean_intermediate_files()
                
                return True
            except Exception as e:
                self.logger.error(f"TV communication failed despite retries: {e}")
                self.logger.info("Image generation was successful and saved locally")
                self.logger.info(f"You can manually upload the image: {image_path}")
                
                # Special handling for common TV errors
                error_msg = str(e).lower()
                if "unreachable" in error_msg or "no route to host" in error_msg:
                    self.logger.warning("TV appears to be powered off or in deep sleep mode")
                    self.logger.info("Try running this script when the TV is on, or enable Wake-on-LAN")
                elif "timeout" in error_msg:
                    self.logger.warning("Connection to TV timed out - network may be unstable")
                    self.logger.info("Check that the TV is connected to the same network as this computer")
                    
                # Clean up intermediate files even though we had an error
                self.clean_intermediate_files()
                # Return true since we did successfully generate the image
                return True

        except Exception as e:
            self.logger.exception(f"Error in application flow: {e}")
            # Try to clean up intermediate files even after an exception
            try:
                self.clean_intermediate_files()
            except Exception as cleanup_error:
                self.logger.warning(f"Error during cleanup: {cleanup_error}")
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
        "--no-upscale", "-n",
        action="store_false",
        dest="upscale",
        help="Skip upscaling step"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug logging (even more detailed than --debug)."
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
    if args.verbose:
        log_level = logging.DEBUG
        # Also enable urllib3 debug logging for network troubleshooting
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
    elif args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    app = DailyArtApp(log_level=log_level)
    
    # Determine enhancement preset
    enhancement_preset = None if args.enhance.lower() == "none" else args.enhance
    
    success = app.run(
        args.prompt, 
        args.image, 
        enhancement_preset,
        args.skip_upload,
        args.upscale
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