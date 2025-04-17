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

    # Instead of using Topaz's output directory handling, we'll do it manually
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

        # Make sure we have absolute paths
        abs_input_path = os.path.abspath(str(input_path))
        
        # This is just a basic try-except block
        try:
            # First try with the standard CLI approach
            logger.info(f"Running Topaz Photo AI on: {abs_input_path}")
            
            # Run the CLI command
            command = [
                tpai_exe,
                "--cli",
                abs_input_path,
                "--upscale",
                "--overwrite"
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Check if successful - the upscaled image will replace the original
            if result.returncode in [0, 1]:  # 0=success, 1=partial success
                # If successful, the input file should have been replaced with
                # the upscaled version
                if input_path.exists():
                    # Copy the upscaled image to our desired output path
                    shutil.copy2(abs_input_path, output_path)
                    return True, str(output_path), None
                else:
                    return (
                        False,
                        None,
                        "Upscale command succeeded but cannot find output file"
                    )
            
            # If regular command failed, try with shell=True and quoted paths
            logger.warning(
                f"First approach failed with return code {result.returncode}. "
                f"Error: {result.stderr}"
            )
            logger.info("Trying alternative approach with shell=True...")
            
            # Build command with quoted paths for shell execution
            shell_cmd = f'{tpai_exe} --cli "{abs_input_path}" --upscale --overwrite'
            
            result = subprocess.run(
                shell_cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Check if this attempt was successful
            if result.returncode in [0, 1]:
                # If successful, the input file should have been replaced
                if input_path.exists():
                    # Copy the upscaled image to our desired output path
                    shutil.copy2(abs_input_path, output_path)
                    return True, str(output_path), None
            
            # If both approaches failed, return error
            debug_info = (
                f"Command: {shell_cmd}\n"
                f"Return code: {result.returncode}\n"
                f"Stderr: {result.stderr}\n"
                f"Stdout: {result.stdout}\n"
            )
            
            return False, None, f"Topaz Photo AI failed: {debug_info}"
        except Exception as e:
            return False, None, f"Error with CLI execution: {str(e)}"

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

