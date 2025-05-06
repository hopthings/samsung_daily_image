#!/usr/bin/env python3
"""
Module for upscaling images using PIL with Lanczos resampling.
Compatible with Raspberry Pi and simpler than RealESRGAN.
"""

import sys
import logging
from pathlib import Path
import tempfile
import shutil
from typing import Optional, Union, Tuple
from PIL import Image, ImageFilter, ImageEnhance

# Set up a logger for this module
logger = logging.getLogger(__name__)


def upscale_image(
    input_path: Union[str, Path]
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Upscale an image using PIL's high-quality Lanczos resampling.
    This is a lightweight alternative to TopazPhoto AI that works on
    Raspberry Pi.

    Args:
        input_path: Path to the image file to upscale

    Returns:
        Tuple of (success, output_path, error_message)
        - success: Boolean indicating if operation was successful
        - output_path: Path to the upscaled image if successful, None otherwise
        - error_message: Error message if operation failed, None otherwise
    """
    # Convert input path to Path object for easier handling
    input_path = Path(input_path)

    # Validate input file
    if not input_path.exists():
        return False, None, f"Input file does not exist: {input_path}"

    if not input_path.is_file():
        return False, None, f"Input path is not a file: {input_path}"

    # Create output filename with -upgraded suffix
    output_path = input_path.parent / (
        f"{input_path.stem}-upgraded{input_path.suffix}"
    )

    # Create temporary directory to work in
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Create temporary file paths
            temp_input = Path(temp_dir) / input_path.name
            abs_temp_input = str(temp_input.absolute())
            # Copy input file to temp directory
            shutil.copy2(input_path, temp_input)
            logger.info(f"Processing image: {abs_temp_input}")
            # Load the image
            img = Image.open(abs_temp_input).convert('RGB')
            # Get original dimensions
            orig_width, orig_height = img.size
            logger.info(f"Original dimensions: {orig_width}x{orig_height}")
            # Calculate new dimensions (2x upscaling)
            new_width = orig_width * 2
            new_height = orig_height * 2
            # Apply a slight sharpening filter first for better details
            img = img.filter(ImageFilter.SHARPEN)
            # Resize the image using high-quality Lanczos resampling
            img_upscaled = img.resize(
                (new_width, new_height),
                resample=Image.Resampling.LANCZOS
            )
            # Enhance the upscaled image
            # Apply sharpening to counter the softness from upscaling
            enhancer = ImageEnhance.Sharpness(img_upscaled)
            img_enhanced = enhancer.enhance(1.2)  # 1.2x sharpening
            # Apply slight contrast enhancement
            contrast_enhancer = ImageEnhance.Contrast(img_enhanced)
            img_enhanced = contrast_enhancer.enhance(1.05)  # 1.05x contrast
            # Save the result to output path
            img_enhanced.save(
                output_path,
                quality=95,  # High quality JPEG
                optimize=True  # Optimize file size
            )
            if output_path.exists():
                logger.info(f"Upscaled image saved to: {output_path}")
                logger.info(f"New dimensions: {new_width}x{new_height}")
                return True, str(output_path), None
            else:
                return False, None, "Failed to save output file"
        except Exception as e:
            return False, None, f"Error during upscaling: {str(e)}"


def main() -> int:
    """
    Main function when script is run directly.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Check if input file was provided
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <image_path>")
        return 1

    # Get input file
    input_file = sys.argv[1]

    # Upscale the image
    success, output_path, error = upscale_image(input_file)

    # Print result
    if success:
        print(f"Successfully upscaled image to: {output_path}")
        return 0
    else:
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
