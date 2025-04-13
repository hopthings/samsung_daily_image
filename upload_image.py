#!/usr/bin/env python3
"""Module for uploading images to Samsung Frame TV."""

import os
import sys
import time
import urllib3  # type: ignore
import logging
import socket
import requests
from typing import Optional, Any, Callable, TypeVar, cast, Type, Tuple
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS  # type: ignore
from samsungtvws.exceptions import HttpApiError  # type: ignore


# Suppress InsecureRequestWarning for local TV connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logger
logger = logging.getLogger("DailyArtApp")

# Type variable for retry decorator
T = TypeVar('T')
ExceptionTypes = Tuple[Type[Exception], ...]


# Retry decorator
def retry(
    max_attempts: int = 5, 
    delay: float = 5.0,
    backoff_factor: float = 2.0,
    allowed_exceptions: ExceptionTypes = (
        HttpApiError, ConnectionError, OSError, TimeoutError
    )
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff_factor: Backoff factor to increase delay between retries.
        allowed_exceptions: Exceptions that trigger a retry.
        
    Returns:
        Decorated function with retry logic.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempts}/{max_attempts} failed with "
                        f"{type(e).__name__}: {e}. "
                        f"Retrying in {current_delay:.1f} seconds..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # This should never be reached, but mypy requires a return statement
            assert False, "This code should be unreachable"
            return cast(T, None)  # Make mypy happy
            
        return wrapper
    return decorator


class TVImageUploader:
    """Class to handle image upload and display on Samsung Frame TV."""

    def __init__(self, tv_ip: Optional[str] = None) -> None:
        """Initialize the uploader with TV IP address.

        Args:
            tv_ip: The IP address of the Samsung TV. If None, it will
                  be loaded from the SAMSUNG_TV_IP environment variable.
        """
        if not tv_ip:
            load_dotenv()
            env_ip = os.getenv("SAMSUNG_TV_IP")
            if not env_ip:
                logger.error("Error: SAMSUNG_TV_IP not found in .env file")
                sys.exit(1)
            tv_ip = env_ip

        self.tv_ip = tv_ip
        self.tv: Any = None
        self._initialize_tv_connection()
        
    def is_tv_available(self) -> bool:
        """Check if the TV is available on the network.
        
        Returns:
            True if TV responds to connection attempt, False otherwise.
        """
        try:
            # Try a simple socket connection to test if the TV is available
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)  # 5 second timeout
            result = sock.connect_ex((self.tv_ip, 8002))
            sock.close()
            
            if result == 0:
                # Additionally check if API endpoint responds
                try:
                    response = requests.get(
                        f"https://{self.tv_ip}:8002/api/v2/", 
                        timeout=5.0,
                        verify=False
                    )
                    return response.status_code < 500  # Any response that's not a server error
                except requests.RequestException:
                    return False
            return False
        except Exception as e:
            logger.debug(f"TV availability check failed: {e}")
            return False  # type: ignore
            
    @retry(max_attempts=5, delay=10.0)
    def _initialize_tv_connection(self) -> None:
        """Initialize connection to the TV with retry logic."""
        logger.info(f"Connecting to Samsung TV at {self.tv_ip}...")
        
        # First check if TV is available
        if not self.is_tv_available():
            logger.warning(f"TV at {self.tv_ip} appears to be unreachable or powered off")
            raise ConnectionError("TV is unreachable - it may be powered off or in deep sleep mode")
            
        # Proceed with actual connection
        self.tv = SamsungTVWS(
            self.tv_ip, 
            port=8002, 
            name="DailyArtApp",
            timeout=10  # Increase default timeout
        )
        logger.info("Successfully connected to Samsung TV")

    @retry(max_attempts=5, delay=5.0)
    def upload_image(self, image_path: str) -> Optional[str]:
        """Upload an image to the TV.

        Args:
            image_path: Path to the image file to upload.

        Returns:
            Content ID if successful, None otherwise.
        """
        if not os.path.exists(image_path):
            logger.error(f"Error: Image {image_path} not found")
            return None

        # Read the image file as binary data
        with open(image_path, 'rb') as f:
            data = f.read()

        # Determine file type from extension
        file_type = os.path.splitext(image_path)[1][1:].upper()
        if file_type.upper() == 'JPG':
            file_type = 'JPEG'

        # Upload the image with no matte/mount
        # Setting matte to 'none' means no frame/mount
        content_id = self.tv.art().upload(  # type: ignore
            data,
            file_type=file_type,
            matte='none',  # No frame/mount
            portrait_matte='none'  # For portrait orientation
        )
        logger.info(f"Uploaded image without matte, content ID: {content_id}")
        return cast(Optional[str], content_id)

    @retry(max_attempts=5, delay=5.0)
    def set_active_art(self, content_id: str) -> bool:
        """Set an uploaded image as the active art.

        Args:
            content_id: The content ID of the image to set as active.

        Returns:
            True if successful, False otherwise.
        """
        # Try to ensure TV is in Art Mode
        try:
            self.tv.art().set_artmode(True)  # type: ignore
            logger.info("Set TV to Art Mode")
        except Exception as e:
            # Art mode switching sometimes fails, but we can still
            # set the active image
            logger.warning(f"Could not set Art Mode: {e}")

        # First remove any matte/mount
        try:
            # Set matte to 'none' to remove any frame/mount
            self.tv.art().change_matte(content_id, matte_id='none')  # type: ignore
            logger.info(f"Removed matte for content ID: {content_id}")
        except Exception as e:
            logger.warning(f"Could not remove matte: {e}")
            # Continue anyway - not critical

        # Set the image as active
        try:
            self.tv.art().select_image(content_id)  # type: ignore
            logger.info(f"Set image with ID: {content_id} as active")
            return True
        except Exception as e:
            logger.warning(f"Could not set primary image as active: {e}")

            # Try alternative approach
            logger.info("Trying alternative approach to set active image")
            content_list = self.tv.art().get_content_list()  # type: ignore
            
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
                    target_id = cast(str, content_list[0].get("content_id"))
                    logger.info(f"Using first available image with ID: {target_id}")

                # First try to remove matte for the target image
                try:
                    # Set matte to 'none' to remove any frame/mount
                    self.tv.art().change_matte(  # type: ignore
                        target_id, matte_id='none'
                    )
                    logger.info(f"Removed matte for alt ID: {target_id}")
                except Exception as e:
                    logger.warning(f"Could not remove matte for alt image: {e}")

                # Then set as active
                self.tv.art().select_image(target_id)  # type: ignore
                logger.info(f"Set alt image ID: {target_id} as active")
                return True
            
            logger.error("No content available to set as active")
            return False
