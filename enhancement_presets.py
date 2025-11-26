#!/usr/bin/env python3
"""Image enhancement presets for comparison and selection."""

import os
import sys
import argparse
from typing import Any, Dict, List, Optional
from image_enhancement import (
    load_image,
    save_image,
    apply_enhancement,
    create_comparison_grid
)


def get_preset_params() -> Dict[str, Dict[str, Any]]:
    """Get a dictionary of preset enhancement parameters.
    
    Returns:
        Dictionary of presets with their parameters
    """
    return {
        "original": {  # Just for comparison
            "sharpness": 1.0,
            "contrast": 1.0,
            "brightness": 1.0,
            "color": 1.0,
            "upscale_factor": 1.0,
            "unsharp_mask": False,
            "unsharp_radius": 0,
            "unsharp_percent": 0,
            "unsharp_threshold": 0,
        },
        "mild": {
            "sharpness": 1.3,
            "contrast": 1.1,
            "brightness": 1.0,
            "color": 1.05,
            "upscale_factor": 1.0,
            "unsharp_mask": False,
            "unsharp_radius": 2.0,
            "unsharp_percent": 150,
            "unsharp_threshold": 3,
        },
        "medium": {
            "sharpness": 1.5,
            "contrast": 1.2,
            "brightness": 1.05,
            "color": 1.1,
            "upscale_factor": 1.0,
            "unsharp_mask": True,
            "unsharp_radius": 2.0,
            "unsharp_percent": 150,
            "unsharp_threshold": 3,
        },
        "strong": {
            "sharpness": 2.0,
            "contrast": 1.3,
            "brightness": 1.1,
            "color": 1.2,
            "upscale_factor": 1.0,
            "unsharp_mask": True,
            "unsharp_radius": 3.0,
            "unsharp_percent": 200,
            "unsharp_threshold": 2,
        },
        "tv-optimized": {
            "sharpness": 1.7,
            "contrast": 1.25,
            "brightness": 1.05,
            "color": 1.15,
            "upscale_factor": 1.2,  # Slight upscale
            "unsharp_mask": True,
            "unsharp_radius": 2.0,
            "unsharp_percent": 180,
            "unsharp_threshold": 3,
        },
        "sharp-only": {
            "sharpness": 2.0,
            "contrast": 1.0,
            "brightness": 1.0,
            "color": 1.0,
            "upscale_factor": 1.0,
            "unsharp_mask": False,
            "unsharp_radius": 2.0,
            "unsharp_percent": 150,
            "unsharp_threshold": 3,
        },
        "unsharp-only": {
            "sharpness": 1.0,
            "contrast": 1.0,
            "brightness": 1.0,
            "color": 1.0,
            "upscale_factor": 1.0,
            "unsharp_mask": True,
            "unsharp_radius": 2.0,
            "unsharp_percent": 200,
            "unsharp_threshold": 3,
        },
        "upscale-only": {
            "sharpness": 1.0,
            "contrast": 1.0,
            "brightness": 1.0,
            "color": 1.0,
            "upscale_factor": 1.5,
            "unsharp_mask": False,
            "unsharp_radius": 2.0,
            "unsharp_percent": 150,
            "unsharp_threshold": 3,
        },
        "upscale-sharp": {
            "sharpness": 1.5,
            "contrast": 1.0,
            "brightness": 1.0,
            "color": 1.0,
            "upscale_factor": 2.0,
            "unsharp_mask": True,
            "unsharp_radius": 2.0,
            "unsharp_percent": 200,
            "unsharp_threshold": 3,
        },
    }


def process_with_presets(
    input_path: str,
    output_dir: str,
    selected_presets: Optional[List[str]] = None
) -> List[str]:
    """Process an image with multiple presets and return file paths.
    
    Args:
        input_path: Path to the input image
        output_dir: Directory to save enhanced images
        selected_presets: List of preset names to use (or None for all)
        
    Returns:
        List of paths to the enhanced images
    """
    # Get all available presets
    presets = get_preset_params()
    
    # Filter presets if selection provided
    if selected_presets:
        presets = {name: params for name, params in presets.items() 
                 if name in selected_presets}
    
    # Skip 'original' preset as it doesn't modify the image
    if 'original' in presets:
        del presets['original']
    
    # Process the image with each preset
    enhanced_paths = []
    enhanced_names = []
    
    # Load the image once
    image = load_image(input_path)
    if not image:
        return []
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get original dimensions
    orig_width, orig_height = image.size
    print(f"Original size: {orig_width}x{orig_height}")
    
    for name, params in presets.items():
        print(f"\nApplying preset: {name}")
        
        # Create descriptive filename
        base_name = os.path.basename(input_path)
        name_root, ext = os.path.splitext(base_name)
        output_filename = f"{name_root}_{name}{ext}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Apply enhancement
        enhanced = apply_enhancement(image, **params)
        
        # Save the enhanced image
        if save_image(enhanced, output_path):
            enhanced_paths.append(output_path)
            enhanced_names.append(name)
            
            # Print enhancement details
            new_width, new_height = enhanced.size
            print(f"Enhanced size: {new_width}x{new_height}")
            print(f"Saved to: {output_path}")
    
    return enhanced_paths, enhanced_names


def main() -> None:
    """Parse arguments and run preset comparisons."""
    parser = argparse.ArgumentParser(description="Compare image enhancement presets")
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
        "--presets", "-p",
        nargs="*",
        help="Specific presets to use (default: all presets)"
    )
    parser.add_argument(
        "--grid",
        action="store_true",
        default=True,
        help="Create a comparison grid (default: True)"
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get available presets
    available_presets = list(get_preset_params().keys())
    
    # Validate requested presets
    if args.presets:
        for preset in args.presets:
            if preset not in available_presets:
                print(f"Warning: Unknown preset '{preset}'")
                print(f"Available presets: {', '.join(available_presets)}")
                sys.exit(1)
    
    # Apply all presets to the image
    enhanced_paths, enhanced_names = process_with_presets(
        args.input, 
        args.output_dir,
        args.presets
    )
    
    # Create comparison grid if requested
    if args.grid and enhanced_paths:
        grid_path = os.path.join(args.output_dir, "comparison_grid.jpg")
        if create_comparison_grid(
            args.input,
            enhanced_paths,
            grid_path,
            enhanced_names
        ):
            print(f"\nComparison grid saved to: {grid_path}")


if __name__ == "__main__":
    main()