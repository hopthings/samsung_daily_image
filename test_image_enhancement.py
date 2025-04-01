#!/usr/bin/env python3
"""Test script for image enhancement experimentation."""

import os
import sys
import argparse
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageEnhance, ImageFilter
import time


def load_image(image_path: str) -> Optional[Image.Image]:
    """Load an image from the specified path.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Loaded PIL Image object or None if loading fails
    """
    if not os.path.exists(image_path):
        print(f"Error: Image {image_path} not found")
        return None
    
    try:
        return Image.open(image_path)
    except Exception as e:
        print(f"Error loading image: {e}")
        return None


def save_image(image: Image.Image, output_path: str) -> bool:
    """Save a PIL Image to the specified path.
    
    Args:
        image: PIL Image to save
        output_path: Path where image should be saved
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save with maximum quality
        image.save(output_path, quality=95, optimize=True)
        print(f"Image saved to {output_path}")
        return True
    except Exception as e:
        print(f"Error saving image: {e}")
        return False


def apply_enhancement(
    image: Image.Image, 
    sharpness: float = 1.0,
    contrast: float = 1.0,
    brightness: float = 1.0,
    color: float = 1.0,
    upscale_factor: float = 1.0,
    unsharp_mask: bool = False,
    unsharp_radius: float = 2.0,
    unsharp_percent: int = 150,
    unsharp_threshold: int = 3,
) -> Image.Image:
    """Apply various enhancements to an image.
    
    Args:
        image: PIL Image to enhance
        sharpness: Sharpness factor (1.0 = unchanged)
        contrast: Contrast factor (1.0 = unchanged)
        brightness: Brightness factor (1.0 = unchanged)
        color: Color factor (1.0 = unchanged)
        upscale_factor: Factor by which to upscale (1.0 = unchanged)
        unsharp_mask: Whether to apply unsharp mask filter
        unsharp_radius: Radius for unsharp mask
        unsharp_percent: Percent for unsharp mask
        unsharp_threshold: Threshold for unsharp mask
        
    Returns:
        Enhanced PIL Image
    """
    # Apply enhancements in a sensible order
    result = image.copy()
    
    # First upscale if requested (before other enhancements)
    if upscale_factor > 1.0:
        new_width = int(result.width * upscale_factor)
        new_height = int(result.height * upscale_factor)
        # Use LANCZOS resampling for best quality
        result = result.resize((new_width, new_height), Image.LANCZOS)
    
    # Apply brightness adjustment
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(result)
        result = enhancer.enhance(brightness)
    
    # Apply color adjustment
    if color != 1.0:
        enhancer = ImageEnhance.Color(result)
        result = enhancer.enhance(color)
    
    # Apply contrast adjustment (after brightness and color)
    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(result)
        result = enhancer.enhance(contrast)
    
    # Apply regular sharpness (before unsharp mask if both are used)
    if sharpness != 1.0:
        enhancer = ImageEnhance.Sharpness(result)
        result = enhancer.enhance(sharpness)
    
    # Apply unsharp mask if requested (often better than simple sharpening)
    if unsharp_mask:
        result = result.filter(
            ImageFilter.UnsharpMask(
                radius=unsharp_radius,
                percent=unsharp_percent,
                threshold=unsharp_threshold
            )
        )
    
    return result


def process_image(
    input_path: str, 
    output_dir: str, 
    params: Dict[str, Any]
) -> Optional[str]:
    """Process an image with the specified enhancement parameters.
    
    Args:
        input_path: Path to the input image
        output_dir: Directory to save the enhanced image
        params: Dictionary of enhancement parameters
        
    Returns:
        Path to the enhanced image if successful, None otherwise
    """
    # Load the image
    image = load_image(input_path)
    if not image:
        return None
    
    # Get original dimensions for filename
    orig_width, orig_height = image.size
    
    # Apply enhancements
    start_time = time.time()
    enhanced = apply_enhancement(image, **params)
    process_time = time.time() - start_time
    
    # Get new dimensions
    new_width, new_height = enhanced.size
    
    # Create descriptive filename
    base_name = os.path.basename(input_path)
    name, ext = os.path.splitext(base_name)
    
    # Include parameters in filename for easier comparison
    param_str = f"s{params['sharpness']}_c{params['contrast']}_b{params['brightness']}"
    if params['upscale_factor'] > 1.0:
        param_str += f"_up{params['upscale_factor']}"
    if params['unsharp_mask']:
        param_str += f"_um{params['unsharp_radius']}-{params['unsharp_percent']}"
    
    # Create output path with descriptive filename
    output_filename = f"{name}_{param_str}{ext}"
    output_path = os.path.join(output_dir, output_filename)
    
    # Save the enhanced image
    if save_image(enhanced, output_path):
        # Print details about the processing
        print(f"Processing time: {process_time:.2f} seconds")
        print(f"Original size: {orig_width}x{orig_height}")
        print(f"New size: {new_width}x{new_height}")
        return output_path
    
    return None


def create_comparison_grid(
    original_path: str,
    enhanced_paths: list,
    output_path: str,
    labels: Optional[list] = None
) -> bool:
    """Create a grid image comparing original and enhanced versions.
    
    Args:
        original_path: Path to the original image
        enhanced_paths: List of paths to enhanced images
        output_path: Path where comparison grid should be saved
        labels: Optional list of labels for enhanced images
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load original image
        original = load_image(original_path)
        if not original:
            return False
        
        # Load enhanced images
        enhanced_images = []
        for path in enhanced_paths:
            img = load_image(path)
            if img:
                enhanced_images.append(img)
        
        if not enhanced_images:
            print("No enhanced images to compare")
            return False
        
        # Default labels if not provided
        if not labels:
            labels = [f"Enhanced {i+1}" for i in range(len(enhanced_images))]
        
        # Calculate grid dimensions
        total_images = len(enhanced_images) + 1  # +1 for original
        if total_images <= 2:
            cols, rows = total_images, 1
        elif total_images <= 4:
            cols, rows = 2, 2
        else:
            cols = 3
            rows = (total_images + cols - 1) // cols
        
        # Resize all images to same size (use dimensions of smallest image)
        width, height = original.size
        for img in enhanced_images:
            w, h = img.size
            if w < width:
                width = w
            if h < height:
                height = h
        
        thumbnail_size = (width, height)
        original_thumb = original.resize(thumbnail_size, Image.LANCZOS)
        enhanced_thumbs = [img.resize(thumbnail_size, Image.LANCZOS) for img in enhanced_images]
        
        # Create blank canvas for grid
        grid_width = cols * width
        grid_height = rows * height
        grid = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        
        # Add images to grid
        thumbnails = [original_thumb] + enhanced_thumbs
        labels = ["Original"] + labels
        
        for i, (thumb, label) in enumerate(zip(thumbnails, labels)):
            row = i // cols
            col = i % cols
            x = col * width
            y = row * height
            grid.paste(thumb, (x, y))
            
            # Could add labels here if we had a drawing library
        
        # Save grid image
        return save_image(grid, output_path)
        
    except Exception as e:
        print(f"Error creating comparison grid: {e}")
        return False


def main() -> None:
    """Parse arguments and run image enhancement tests."""
    parser = argparse.ArgumentParser(description="Test image enhancement techniques")
    parser.add_argument(
        "--input", "-i",
        default="sample_image.jpeg",
        help="Path to input image (default: sample_image.jpeg)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="enhanced_images",
        help="Directory to save enhanced images (default: enhanced_images)"
    )
    parser.add_argument(
        "--sharpness", "-s",
        type=float,
        default=1.5,
        help="Sharpness enhancement factor (default: 1.5)"
    )
    parser.add_argument(
        "--contrast", "-c",
        type=float,
        default=1.2,
        help="Contrast enhancement factor (default: 1.2)"
    )
    parser.add_argument(
        "--brightness", "-b",
        type=float,
        default=1.0,
        help="Brightness enhancement factor (default: 1.0)"
    )
    parser.add_argument(
        "--color", "-k",
        type=float,
        default=1.1,
        help="Color enhancement factor (default: 1.1)"
    )
    parser.add_argument(
        "--upscale", "-u",
        type=float,
        default=1.0,
        help="Upscale factor (default: 1.0, no upscaling)"
    )
    parser.add_argument(
        "--unsharp-mask",
        action="store_true",
        help="Apply unsharp mask filter"
    )
    parser.add_argument(
        "--unsharp-radius",
        type=float,
        default=2.0,
        help="Unsharp mask radius (default: 2.0)"
    )
    parser.add_argument(
        "--unsharp-percent",
        type=int,
        default=150,
        help="Unsharp mask percent (default: 150)"
    )
    parser.add_argument(
        "--unsharp-threshold",
        type=int,
        default=3,
        help="Unsharp mask threshold (default: 3)"
    )
    parser.add_argument(
        "--grid",
        action="store_true",
        help="Create a comparison grid with original and enhanced image"
    )
    parser.add_argument(
        "--preset",
        choices=["mild", "medium", "strong", "tv-optimized"],
        help="Use a predefined preset instead of individual parameters"
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Apply presets if specified
    if args.preset:
        if args.preset == "mild":
            params = {
                "sharpness": 1.3,
                "contrast": 1.1,
                "brightness": 1.0,
                "color": 1.05,
                "upscale_factor": 1.0,
                "unsharp_mask": False,
                "unsharp_radius": 2.0,
                "unsharp_percent": 150,
                "unsharp_threshold": 3,
            }
        elif args.preset == "medium":
            params = {
                "sharpness": 1.5,
                "contrast": 1.2,
                "brightness": 1.05,
                "color": 1.1,
                "upscale_factor": 1.0,
                "unsharp_mask": True,
                "unsharp_radius": 2.0,
                "unsharp_percent": 150,
                "unsharp_threshold": 3,
            }
        elif args.preset == "strong":
            params = {
                "sharpness": 2.0,
                "contrast": 1.3,
                "brightness": 1.1,
                "color": 1.2,
                "upscale_factor": 1.0,
                "unsharp_mask": True,
                "unsharp_radius": 3.0,
                "unsharp_percent": 200,
                "unsharp_threshold": 2,
            }
        elif args.preset == "tv-optimized":
            params = {
                "sharpness": 1.7,
                "contrast": 1.25,
                "brightness": 1.05,
                "color": 1.15,
                "upscale_factor": 1.2,  # Slight upscale
                "unsharp_mask": True,
                "unsharp_radius": 2.0,
                "unsharp_percent": 180,
                "unsharp_threshold": 3,
            }
    else:
        # Use individual parameters
        params = {
            "sharpness": args.sharpness,
            "contrast": args.contrast,
            "brightness": args.brightness,
            "color": args.color,
            "upscale_factor": args.upscale,
            "unsharp_mask": args.unsharp_mask,
            "unsharp_radius": args.unsharp_radius,
            "unsharp_percent": args.unsharp_percent,
            "unsharp_threshold": args.unsharp_threshold,
        }
    
    # Process the image
    enhanced_path = process_image(args.input, args.output_dir, params)
    
    if enhanced_path and args.grid:
        # Create comparison grid
        grid_path = os.path.join(args.output_dir, "comparison_grid.jpg")
        create_comparison_grid(
            args.input,
            [enhanced_path],
            grid_path
        )


if __name__ == "__main__":
    main()