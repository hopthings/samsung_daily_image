#!/usr/bin/env python3
"""
Module for upscaling images using Topaz Photo AI CLI.
"""

import subprocess
import tempfile
import sys
import platform
import os
import logging
import shutil
from pathlib import Path
from typing import Optional, Union, Tuple

# Set up a logger for this module
logger = logging.getLogger(__name__)


def upscale_image(
    input_path: Union[str, Path]
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Upscale an image using Topaz Photo AI.

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
            # Determine Topaz executable path based on OS
            if platform.system() == "Darwin":  # macOS
                tpai_exe = "tpai"
            elif platform.system() == "Windows":
                tpai_exe = (
                    r"C:\Program Files\Topaz Labs LLC\Topaz Photo AI\tpai.exe"
                )
            else:
                return (
                    False,
                    None,
                    f"Unsupported operating system: {platform.system()}"
                )

            # Create a temporary copy of the input file
            temp_input = Path(temp_dir) / input_path.name
            shutil.copy2(input_path, temp_input)
            
            # Absolute path to the temp input file
            abs_temp_input = str(temp_input.absolute())
            
            # First try with the standard CLI approach
            logger.info(f"Running Topaz Photo AI on: {abs_temp_input}")
            
            # Run the CLI command 
            command = [
                tpai_exe,
                "--cli",
                abs_temp_input,
                "--upscale",
                "--overwrite"
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )
            
            success = False
            
            # Check if the command succeeded
            if result.returncode in [0, 1]:  # 0=success, 1=partial success
                if temp_input.exists():
                    # Copy the upscaled temp file to our output path
                    shutil.copy2(temp_input, output_path)
                    success = True
            
            # If first attempt failed, try alternative approach with shell=True
            if not success:
                logger.warning(
                    f"First approach failed with return code {result.returncode}. "
                    f"Error: {result.stderr}"
                )
                logger.info("Trying alternative approach with shell=True...")
                
                # Re-copy the original to the temp location (in case it was modified)
                if temp_input.exists():
                    os.remove(temp_input)
                shutil.copy2(input_path, temp_input)
                
                # Build command with quoted paths for shell execution
                shell_cmd = f'{tpai_exe} --cli "{abs_temp_input}" --upscale --overwrite'
                
                result = subprocess.run(
                    shell_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                # Check if second attempt succeeded
                if result.returncode in [0, 1]:
                    if temp_input.exists():
                        shutil.copy2(temp_input, output_path)
                        success = True
            
            # Return result based on success flag
            if success:
                if output_path.exists():
                    return True, str(output_path), None
                else:
                    return False, None, "Failed to create output file"
            else:
                # Prepare debug info for error reporting
                debug_info = (
                    f"Command: {command if isinstance(command, str) else ' '.join(str(x) for x in command)}\n"
                    f"Return code: {result.returncode}\n"
                    f"Stderr: {result.stderr}\n"
                    f"Stdout: {result.stdout}\n"
                )
                return False, None, f"Topaz Photo AI failed: {debug_info}"
                
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

