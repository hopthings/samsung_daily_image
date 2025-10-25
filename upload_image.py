#!/usr/bin/env python3
"""Module for uploading images to Samsung Frame TV."""

import os
import sys
import time
import urllib3
import logging
import socket
import requests
import threading
from typing import Optional, Any, Callable, TypeVar, cast, Type, Tuple
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS  # type: ignore # Missing module typings
from samsungtvws.exceptions import HttpApiError  # Missing module typings


# Suppress InsecureRequestWarning for local TV connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logger
logger = logging.getLogger("DailyArtApp")

# Type variable for retry decorator
T = TypeVar('T')
ExceptionTypes = Tuple[Type[Exception], ...]


class UploadTimeoutError(Exception):
    """Raised when upload exceeds timeout threshold."""
    pass


class DeviceConflictError(Exception):
    """Raised when another device interferes with upload."""
    pass


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


def with_timeout(timeout_seconds: int, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Execute a function with a hard timeout.

    Args:
        timeout_seconds: Maximum seconds to wait
        func: Function to execute
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result from func

    Raises:
        UploadTimeoutError: If function exceeds timeout
    """
    result: list[Optional[T]] = [None]
    exception: list[Optional[Exception]] = [None]

    def target() -> None:
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        # Thread is still running - timeout occurred
        logger.error(f"Upload exceeded {timeout_seconds}s timeout - killing upload attempt")
        raise UploadTimeoutError(f"Upload exceeded {timeout_seconds}s timeout")

    if exception[0]:
        raise exception[0]

    return result[0]  # type: ignore


def is_device_conflict_error(error: Exception) -> bool:
    """Check if an error is due to another device connecting.

    Args:
        error: Exception to check

    Returns:
        True if error is due to device conflict
    """
    error_str = str(error).lower()
    error_repr = repr(error).lower()

    # Check for device conflict indicators
    conflict_indicators = [
        'clientconnect',
        'smart device',
        'device conflict',
        'another device',
        'concurrent connection'
    ]

    for indicator in conflict_indicators:
        if indicator in error_str or indicator in error_repr:
            return True

    return False


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
            return False

    def check_network_stability(self) -> bool:
        """Check network stability by performing multiple rapid connection tests.
        
        Returns:
            True if network appears stable, False otherwise.
        """
        logger.info("Checking network stability before upload...")
        stable_connections = 0
        total_tests = 5
        
        for i in range(total_tests):
            try:
                # Quick socket test
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3.0)
                start_time = time.time()
                result = sock.connect_ex((self.tv_ip, 8002))
                response_time = time.time() - start_time
                sock.close()
                
                if result == 0:
                    stable_connections += 1
                    logger.debug(f"Stability test {i+1}/{total_tests}: OK ({response_time:.2f}s)")
                else:
                    logger.debug(f"Stability test {i+1}/{total_tests}: FAILED")
                
                # Small delay between tests
                time.sleep(0.5)
                
            except Exception as e:
                logger.debug(f"Stability test {i+1}/{total_tests}: ERROR - {e}")
        
        stability_ratio = stable_connections / total_tests
        logger.info(f"Network stability: {stable_connections}/{total_tests} tests passed ({stability_ratio:.0%})")
        
        # Consider stable if 80% or more tests pass
        is_stable = stability_ratio >= 0.8
        
        if not is_stable:
            logger.warning("Network appears unstable - upload may fail or be unreliable")
        else:
            logger.info("Network appears stable for upload")
            
        return is_stable

    def _patient_upload(self, data: bytes, file_type: str) -> Optional[str]:
        """Upload large files using a single patient approach with longer waits.
        
        Args:
            data: Image data to upload
            file_type: File type (JPEG, PNG)
            
        Returns:
            Content ID if successful, None otherwise
        """
        total_size = len(data)
        logger.info(f"Starting patient upload of {total_size/1024/1024:.1f} MB file...")
        
        # Wait longer before starting upload to let TV settle
        logger.info("Waiting 10 seconds for TV to settle before upload...")
        time.sleep(10)
        
        # Ensure we have a clean connection
        if hasattr(self.tv, '_connection'):
            try:
                if hasattr(self.tv._connection, 'close'):
                    self.tv._connection.close()
                self.tv._connection = None
                logger.debug("Closed existing connection for clean start")
                # Wait after closing connection
                time.sleep(5)
            except:
                pass
        
        try:
            logger.info("Starting single patient upload attempt...")
            
            # Use the standard upload but with more patience
            content_id = self.tv.art().upload(
                data,
                file_type=file_type,
                matte='none',
                portrait_matte='none'
            )
            logger.info("Patient upload succeeded!")
            return content_id
                
        except Exception as e:
            logger.error(f"Patient upload failed: {e}")
            
            # If it's a timeout, try to check if upload actually succeeded
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                logger.info("Upload timed out, checking if it might have succeeded...")
                
                # Wait for TV to potentially finish processing
                time.sleep(15)
                
                try:
                    # Check if any new content appeared
                    if hasattr(self.tv.art(), 'get_thumbnail_list'):
                        content_list = self.tv.art().get_thumbnail_list()
                    elif hasattr(self.tv.art(), 'get_list'):
                        content_list = self.tv.art().get_list()
                    elif hasattr(self.tv.art(), 'list'):
                        content_list = self.tv.art().list()
                    else:
                        content_list = []
                    
                    if content_list and len(content_list) > 0:
                        # Get the most recent content ID
                        recent_id = content_list[0].get("content_id")
                        logger.info(f"Found recent content after timeout: {recent_id}")
                        logger.info("Upload may have succeeded despite timeout!")
                        return recent_id
                    else:
                        logger.warning("No content found - upload likely failed")
                        
                except Exception as check_err:
                    logger.debug(f"Content check failed: {check_err}")
            
            return None
            
    @retry(max_attempts=5, delay=10.0)
    def _initialize_tv_connection(self) -> None:
        """Initialize connection to the TV with retry logic."""
        logger.info(f"Connecting to Samsung TV at {self.tv_ip}...")
        
        # First check if TV is available
        logger.debug(f"Checking TV availability at {self.tv_ip}:8002")
        if not self.is_tv_available():
            logger.warning(f"TV at {self.tv_ip} appears to be unreachable or powered off")
            logger.debug("TV availability check failed - socket connection or API check failed")
            raise ConnectionError("TV is unreachable - it may be powered off or in deep sleep mode")
            
        logger.debug("TV availability check passed")
        
        # Proceed with actual connection with increased timeouts
        try:
            logger.debug(f"Creating SamsungTVWS connection with timeout=180")
            self.tv = SamsungTVWS(
                self.tv_ip, 
                port=8002, 
                name="DailyArtApp",
                timeout=180  # Further increased timeout for all operations (3 minutes)
            )
            logger.info("Successfully created Samsung TV connection object")
            
            # Test the connection by trying to get device info
            try:
                logger.debug("Testing TV connection by attempting to get device info")
                if hasattr(self.tv, 'rest_device_info'):
                    device_info = self.tv.rest_device_info()
                    logger.debug(f"Device info response: {device_info}")
                elif hasattr(self.tv, 'info'):
                    info = self.tv.info()
                    logger.debug(f"TV info response: {info}")
                logger.info("TV connection test successful")
            except Exception as test_error:
                logger.warning(f"TV connection test failed but continuing: {test_error}")
                
        except Exception as conn_error:
            logger.error(f"Failed to create TV connection: {conn_error}")
            logger.debug(f"Connection error details: {type(conn_error).__name__}: {conn_error}")
            raise
            
        logger.info("Successfully connected to Samsung TV")

    @retry(max_attempts=8, delay=10.0, backoff_factor=1.5)
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

        # Get the file size to log it
        file_size = os.path.getsize(image_path)
        logger.info(f"Uploading image of size: {file_size/1024/1024:.2f} MB")
        
        # Check network stability before attempting upload
        if not self.check_network_stability():
            logger.warning(
                "Network stability check failed - "
                "proceeding with upload but expect potential issues"
            )
        
        # Calculate expected upload time (more conservative estimate for Pi/WiFi)
        # Assume 1 MB/s upload speed (very conservative for Raspberry Pi over WiFi)
        expected_seconds = file_size / (1 * 1024 * 1024)
        logger.info(f"Expected upload time: approximately {expected_seconds:.1f} seconds")
        
        try:
            # Set a much longer timeout for larger files, especially on Pi
            # 5x expected time, min 5 minutes
            dynamic_timeout = max(300, int(expected_seconds * 5))
            logger.info(f"Setting timeout to {dynamic_timeout}s for upload")
            
            # Temporarily update the connection timeout
            original_timeout = getattr(self.tv, 'timeout', 180)
            logger.debug(f"Original timeout was: {original_timeout}s")
            
            try:
                # Set the dynamic timeout on the TV object
                setattr(self.tv, 'timeout', dynamic_timeout)
                logger.debug(f"Updated TV timeout to: {dynamic_timeout}s")
                
                # Monkey patch the WebSocket library to use our timeout
                original_settimeout = None
                try:
                    import websocket
                    import socket
                    
                    # Store original functions
                    original_settimeout = socket.socket.settimeout
                    
                    def patched_settimeout(self, timeout):
                        # Override any timeout less than our dynamic timeout
                        if timeout is not None and timeout < dynamic_timeout:
                            logger.debug(f"Overriding socket timeout from {timeout}s to {dynamic_timeout}s")
                            timeout = dynamic_timeout
                        return original_settimeout(self, timeout)
                    
                    # Apply the patch
                    socket.socket.settimeout = patched_settimeout
                    logger.debug(f"Applied WebSocket timeout patch for {dynamic_timeout}s")
                    
                except ImportError:
                    logger.debug("Could not patch WebSocket timeout - websocket module not available")
                
                # Force create a new connection with these timeouts
                if hasattr(self.tv, '_connection'):
                    logger.debug("Closing existing TV connection to refresh timeout")
                    if hasattr(self.tv._connection, 'close'):
                        self.tv._connection.close()
                    self.tv._connection = None
                    
                # Log upload parameters
                logger.debug(f"Upload parameters: file_type={file_type}, matte=none, portrait_matte=none")
                logger.info(f"Starting upload of {file_size} bytes...")
                
                # Call upload with hard timeout wrapper and retry logic for device conflicts
                upload_start_time = time.time()
                content_id = None
                max_upload_attempts = 3
                upload_attempt = 0

                # Hard timeout: 30 seconds for files under 5MB, 60 seconds for larger
                hard_timeout = 60 if file_size > 5 * 1024 * 1024 else 30
                logger.info(f"Using hard timeout of {hard_timeout}s for upload")

                while upload_attempt < max_upload_attempts and content_id is None:
                    upload_attempt += 1
                    try:
                        # For large files, try single patient upload approach
                        if file_size > 5 * 1024 * 1024:  # 5MB threshold
                            logger.info(f"Attempt {upload_attempt}/{max_upload_attempts}: Large file upload with {hard_timeout}s timeout...")
                            content_id = with_timeout(
                                hard_timeout,
                                self._patient_upload,
                                data,
                                file_type
                            )
                        else:
                            logger.info(f"Attempt {upload_attempt}/{max_upload_attempts}: Standard upload with {hard_timeout}s timeout...")
                            content_id = with_timeout(
                                hard_timeout,
                                self.tv.art().upload,
                                data,
                                file_type=file_type,
                                matte='none',
                                portrait_matte='none'
                            )

                        # If we got here, upload succeeded
                        if content_id:
                            logger.info(f"Upload succeeded on attempt {upload_attempt}")
                            break

                    except (UploadTimeoutError, DeviceConflictError) as e:
                        if upload_attempt < max_upload_attempts:
                            if isinstance(e, DeviceConflictError):
                                logger.warning(f"Device conflict detected on attempt {upload_attempt}, waiting 10s before retry...")
                                time.sleep(10)  # Wait for interfering device to disconnect
                            else:
                                logger.warning(f"Upload timeout on attempt {upload_attempt}, waiting 5s before retry...")
                                time.sleep(5)

                            # Reset connection for next attempt
                            if hasattr(self.tv, '_connection'):
                                try:
                                    if hasattr(self.tv._connection, 'close'):
                                        self.tv._connection.close()
                                    self.tv._connection = None
                                    logger.debug("Reset connection for retry")
                                except:
                                    pass
                        else:
                            # Final attempt failed
                            logger.error(f"Upload failed after {max_upload_attempts} attempts")
                            raise

                    except Exception as e:
                        # Check if this is a device conflict
                        if is_device_conflict_error(e):
                            logger.warning(f"Device conflict detected: {e}")
                            if upload_attempt < max_upload_attempts:
                                logger.info(f"Waiting 10s for device to disconnect before retry...")
                                time.sleep(10)
                                continue
                        # Re-raise other exceptions
                        raise

                if content_id is None:
                    raise Exception("Upload failed: No content ID returned after all attempts")

                upload_end_time = time.time()
                upload_duration = upload_end_time - upload_start_time
                
                logger.info(f"Upload completed in {upload_duration:.1f} seconds")
                logger.debug(f"Upload speed: {(file_size / upload_duration / 1024 / 1024):.2f} MB/s")
                
            finally:
                # Restore the original timeout
                setattr(self.tv, 'timeout', original_timeout)
                logger.debug(f"Restored TV timeout to: {original_timeout}s")
                
                # Restore original WebSocket functions if we patched them
                try:
                    import socket
                    if original_settimeout is not None:
                        socket.socket.settimeout = original_settimeout
                        logger.debug("Restored original socket.settimeout function")
                except:
                    pass
                
            logger.info(f"Uploaded image without matte, content ID: {content_id}")
            logger.debug(f"Content ID type: {type(content_id)}, value: '{content_id}'")
            
            # Add a significant delay after successful upload to let the TV process it
            delay_seconds = min(15, max(10, int(expected_seconds / 3)))  # At least 10 seconds, or more for larger files
            logger.info(f"Waiting {delay_seconds} seconds for TV to process the image...")
            time.sleep(delay_seconds)
            
            # Save this content ID for debugging and reliable art selection
            try:
                with open("last_uploaded_id.txt", "w") as f:
                    f.write(f"{content_id}")
                logger.info(f"Saved content ID '{content_id}' to last_uploaded_id.txt")
                
                # Also maintain the old filename for backward compatibility
                with open("last_content_id.txt", "w") as f:
                    f.write(f"{content_id}")
                logger.debug(f"Also saved content ID to last_content_id.txt")
            except Exception as e:
                logger.warning(f"Could not save content ID to file: {e}")
            
            return cast(Optional[str], content_id)
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            logger.debug(f"Upload error details: {type(e).__name__}: {e}")
            
            # Log additional error context if available
            if hasattr(e, 'response'):
                logger.debug(f"HTTP response status: {getattr(e.response, 'status_code', 'unknown')}")
                logger.debug(f"HTTP response text: {getattr(e.response, 'text', 'unknown')}")
            
            # If we get a timeout, try to check if the image was actually uploaded
            if "timeout" in str(e).lower():
                logger.info("Timeout during upload. Trying to verify if the upload completed...")
                logger.debug(f"Upload timeout occurred after expected {expected_seconds:.1f}s (timeout was {dynamic_timeout}s)")
                
                try:
                    # Wait a moment for any pending operations
                    logger.debug("Waiting 10 seconds for any pending TV operations...")
                    time.sleep(10)  # Increased wait time
                    
                    # Try to get content list to see if our upload went through
                    logger.debug("Attempting to retrieve content list to check for successful upload...")
                    if hasattr(self.tv.art(), 'get_thumbnail_list'):
                        content_list = self.tv.art().get_thumbnail_list()
                    elif hasattr(self.tv.art(), 'get_list'):
                        content_list = self.tv.art().get_list()
                    elif hasattr(self.tv.art(), 'list'):
                        content_list = self.tv.art().list()
                    else:
                        content_list = []
                    
                    if content_list and len(content_list) > 0:
                        logger.info(f"Found {len(content_list)} items in content list after timeout")
                        # Log found content IDs for debugging
                        ids = [item.get("content_id", "unknown") for item in content_list[:5]]
                        logger.info(f"Recent content IDs: {ids}")
                        
                        # Check if any of these IDs might be our upload
                        logger.debug("Checking if any recent content might be our upload...")
                        for i, item in enumerate(content_list[:3]):
                            content_id = item.get("content_id", "unknown")
                            logger.debug(f"Content {i+1}: ID={content_id}, item={item}")
                        
                        # If we have recent content, the upload might have succeeded
                        if len(content_list) > 0:
                            logger.warning("Upload may have succeeded despite timeout - check TV manually")
                    else:
                        logger.warning("No content found in list after timeout - upload likely failed")
                    
                    # If we reach here without error, the connection is working
                    # but our upload may have timed out. Most likely the image is too large.
                    logger.warning("Upload may have been interrupted due to timeout. "
                                  "Consider using a smaller image or increasing the timeout.")
                except Exception as check_err:
                    logger.debug(f"Content list check failed: {check_err}")
                    logger.debug(f"Check error details: {type(check_err).__name__}: {check_err}")
            
            # Log suggestions based on error type
            error_str = str(e).lower()
            if "connection" in error_str:
                logger.info("Connection error - check TV is on and network is stable")
            elif "ssl" in error_str or "certificate" in error_str:
                logger.info("SSL/Certificate error - this is normal for local TV connections")
            elif "permission" in error_str or "auth" in error_str:
                logger.info("Permission error - check TV allows connections from this device")
            
            # Re-raise the original exception to trigger retry
            raise

    # Specialized retry decorator for the select_image operation
    @retry(max_attempts=15, delay=8.0, backoff_factor=1.5)
    def _select_image_with_retry(self, image_id: str) -> bool:
        """Retry wrapper specifically for the select_image operation.

        Args:
            image_id: Content ID to set as active.

        Returns:
            True if successful, False otherwise.

        Raises:
            Exception: If select_image fails.
        """
        logger.info(f"Attempting to select image with ID: {image_id} (with retries)")

        # Try to verify TV is in art mode first
        try:
            # Check current mode if possible
            if hasattr(self.tv.art(), 'get_artmode'):
                try:
                    current_mode = self.tv.art().get_artmode()
                    logger.info(f"Current art mode status: {current_mode}")
                    if not current_mode:
                        logger.info("TV not in Art Mode, attempting to switch...")
                        self.tv.art().set_artmode(True)
                        time.sleep(5)  # Wait for mode switch
                except Exception as mode_err:
                    logger.warning(f"Could not check art mode status: {mode_err}")
        except Exception as e:
            logger.warning(f"Art mode verification failed: {e}")

        # Now attempt to select the image
        self.tv.art().select_image(image_id)

        # Wait a moment to ensure the selection takes effect
        time.sleep(3)

        logger.info(f"Successfully set image with ID: {image_id} as active")
        return True

    @retry(max_attempts=10, delay=10.0, backoff_factor=1.5)
    def set_active_art(self, content_id: str) -> bool:
        """Set an uploaded image as the active art.

        Args:
            content_id: The content ID of the image to set as active.

        Returns:
            True if successful, False otherwise.
        """
        # Log the content ID we're trying to set
        logger.info(f"Attempting to set content ID as active: {content_id}")

        # Read content ID from file for verification and possible fallback
        stored_id = None
        try:
            # Try the new filename first
            if os.path.exists("last_uploaded_id.txt"):
                with open("last_uploaded_id.txt", "r") as f:
                    stored_id = f.read().strip()
                    if stored_id and stored_id != content_id:
                        logger.warning(f"Warning: Content ID mismatch. File has: {stored_id}, Passed: {content_id}")
                        # We'll still try the provided ID first, but keep the stored one as fallback
            # Try old filename as fallback
            elif os.path.exists("last_content_id.txt"):
                with open("last_content_id.txt", "r") as f:
                    stored_id = f.read().strip()
                    if stored_id and stored_id != content_id:
                        logger.warning(f"Warning: Content ID mismatch from old file. Stored: {stored_id}, Current: {content_id}")
        except Exception as e:
            logger.warning(f"Could not read stored content ID: {e}")

        # Verify TV connectivity before proceeding
        if not self.is_tv_available():
            logger.warning("TV appears to be unreachable - attempting to reconnect...")
            try:
                self._initialize_tv_connection()
                logger.info("Successfully reconnected to TV")
            except Exception as e:
                logger.error(f"Could not reconnect to TV: {e}")
                return False

        # More robust Art Mode switching with multiple attempts
        art_mode_success = False

        # Method 1: Use set_artmode API with verification
        try:
            logger.info("Trying to set TV to Art Mode using set_artmode API...")

            # First check if we're already in Art Mode
            try:
                if hasattr(self.tv.art(), 'get_artmode'):
                    current_art_mode = self.tv.art().get_artmode()
                    if current_art_mode:
                        logger.info("TV is already in Art Mode, skipping mode switch")
                        art_mode_success = True
                    else:
                        logger.info("TV is not in Art Mode, switching now")
            except Exception:
                logger.warning("Could not check current Art Mode status")

            # Only switch if not already successful
            if not art_mode_success:
                self.tv.art().set_artmode(True)
                # Wait longer for Art Mode to fully activate
                time.sleep(10)  # Increased to 10 seconds
                art_mode_success = True
                logger.info("Successfully set TV to Art Mode")
        except Exception as e:
            logger.warning(f"Could not set Art Mode via API: {e}")

        # Method 2: Use KEY_ART remote command if Method 1 failed
        if not art_mode_success:
            try:
                logger.info("Trying to set TV to Art Mode using KEY_ART command...")
                self.tv.send_key("KEY_ART")
                # Wait even longer for this method
                time.sleep(12)  # Increased to 12 seconds
                art_mode_success = True
                logger.info("Sent KEY_ART command to TV")
            except Exception as e:
                logger.warning(f"Could not send KEY_ART command: {e}")

        # Method 3: Last resort try a second KEY_ART
        if not art_mode_success:
            try:
                logger.info("Final attempt to set Art Mode with KEY_ART...")
                # Wait a moment before trying again
                time.sleep(3)
                self.tv.send_key("KEY_ART")
                time.sleep(15)  # Even longer delay on final attempt
                art_mode_success = True
                logger.info("Sent second KEY_ART command to TV")
            except Exception as e:
                logger.warning(f"Could not send second KEY_ART command: {e}")

        if not art_mode_success:
            logger.warning("Could not confirm TV is in Art Mode - proceeding anyway")

        # Get content list early to verify our content_id exists
        content_list = []
        try:
            logger.info("Fetching content list to verify image availability...")
            if hasattr(self.tv.art(), 'get_thumbnail_list'):
                content_list = self.tv.art().get_thumbnail_list()
            elif hasattr(self.tv.art(), 'get_list'):
                content_list = self.tv.art().get_list()
            elif hasattr(self.tv.art(), 'list'):
                content_list = self.tv.art().list()
            else:
                content_list = []
            if content_list:
                logger.info(f"Found {len(content_list)} items in the content list")
                # Check if our content_id is in the list
                found = False
                for item in content_list:
                    if item.get("content_id") == content_id:
                        found = True
                        logger.info(f"Confirmed our content ID {content_id} exists in the content list")
                        break
                if not found:
                    logger.warning(f"Content ID {content_id} not found in content list!")
        except Exception as e:
            logger.warning(f"Could not get content list for verification: {e}")

        # Remove any matte/mount for the art we're trying to set
        try:
            logger.info(f"Removing matte for content ID: {content_id}")
            self.tv.art().change_matte(content_id, matte_id='none')
            # Increased wait time
            time.sleep(5)  # Increased from 2 to 5 seconds
            logger.info("Successfully removed matte")
        except Exception as e:
            logger.warning(f"Could not remove matte: {e}")
            # Continue anyway - not critical

        # Add a longer delay to ensure changes are fully processed by the TV
        logger.info("Waiting 15 seconds before setting active art...")
        time.sleep(15)  # Increased to 15 seconds

        # Try multiple approaches to set the active image, in order of preference

        # Approach 1: Use the content_id directly with retry
        try:
            logger.info(f"Attempt 1: Setting image ID {content_id} as active (with dedicated retry)...")
            logger.debug(f"Using primary select method with content_id: '{content_id}'")
            
            success = self._select_image_with_retry(content_id)
            if success:
                logger.info("Primary select method reported success")
                
                # Double-check by trying to get current displayed image
                try:
                    if hasattr(self.tv.art(), 'get_current'):
                        logger.debug("Attempting to verify current displayed image...")
                        current = self.tv.art().get_current()
                        logger.info(f"Current displayed image info: {current}")
                        
                        # Try to extract and log the current content ID if available
                        if isinstance(current, dict) and 'content_id' in current:
                            current_id = current['content_id']
                            if current_id == content_id:
                                logger.info(f"✓ Verification successful: Current image ID matches our upload: {current_id}")
                            else:
                                logger.warning(f"⚠ Verification warning: Current image ID ({current_id}) does not match our upload ({content_id})")
                        else:
                            logger.debug(f"Current image info format: {type(current)}")
                except Exception as e:
                    logger.debug(f"Could not verify current image: {e}")
                    logger.debug(f"Verification error details: {type(e).__name__}: {e}")
                    
                return True
        except Exception as e:
            logger.warning(f"Primary method to set image failed: {e}")
            logger.debug(f"Primary method error details: {type(e).__name__}: {e}")

        # Approach 2: Get the content list and find our image
        logger.info("Attempt 2: Trying to find our image in the content list...")
        try:
            # If we already have content list from earlier, use it
            if not content_list:
                if hasattr(self.tv.art(), 'get_thumbnail_list'):
                    content_list = self.tv.art().get_thumbnail_list()
                elif hasattr(self.tv.art(), 'get_list'):
                    content_list = self.tv.art().get_list()
                elif hasattr(self.tv.art(), 'list'):
                    content_list = self.tv.art().list()
                else:
                    content_list = []

            if content_list and len(content_list) > 0:
                # Log all available content IDs for debugging
                all_ids = ", ".join([item.get("content_id", "unknown") for item in content_list[:10]])
                logger.info(f"Available content IDs (up to 10): {all_ids}")

                # Look for our specific content_id first
                target_id = None
                found_primary = False
                found_fallback = False

                # First, look for the content_id we were given
                for item in content_list:
                    if item.get("content_id") == content_id:
                        target_id = content_id
                        found_primary = True
                        logger.info(f"Found our primary content ID in the list: {content_id}")
                        break

                # If primary not found but we have a stored fallback, try that
                if not found_primary and stored_id:
                    for item in content_list:
                        if item.get("content_id") == stored_id:
                            target_id = stored_id
                            found_fallback = True
                            logger.info(f"Found our fallback content ID in the list: {stored_id}")
                            break

                # If neither found, use the most recent one (first in list)
                if not found_primary and not found_fallback and len(content_list) > 0:
                    target_id = cast(str, content_list[0].get("content_id"))
                    logger.info(f"Our content IDs not found in list, using most recent: {target_id}")

                if target_id:
                    # Try to remove matte for the target image
                    try:
                        self.tv.art().change_matte(target_id, matte_id='none')
                        logger.info(f"Removed matte for target ID: {target_id}")
                        time.sleep(5)  # Longer delay after matte removal
                    except Exception as e:
                        logger.warning(f"Could not remove matte for target image: {e}")

                    # Try setting the image with retry
                    try:
                        success = self._select_image_with_retry(target_id)
                        if success:
                            return True
                    except Exception as e:
                        logger.warning(f"Could not set target image as active: {e}")
                else:
                    logger.error("No valid target ID found in content list")
            else:
                logger.error("No content available in the list")
        except Exception as e:
            logger.warning(f"Could not get content list: {e}")

        # Approach 3: Try direct REST API call if available
        try:
            logger.info("Attempt 3: Trying direct REST API approach...")
            # This is a fallback method that attempts a more direct approach if available
            if hasattr(self.tv, '_rest_device') and hasattr(self.tv._rest_device, 'send_command'):
                try:
                    logger.info(f"Sending direct select command for content ID: {content_id}")
                    # Note: This is implementation dependent and may not work on all TVs
                    endpoint = 'art/select'
                    data = {"contentId": content_id, "mat": "none"}
                    response = self.tv._rest_device.send_command(endpoint, data)
                    logger.info(f"Direct API response: {response}")
                    return True
                except Exception as e:
                    logger.warning(f"Direct REST API approach failed: {e}")
        except Exception as e:
            logger.warning(f"Error in direct REST API approach: {e}")

        # Approach 4: Final fallback - try once more with stored ID
        if stored_id and stored_id != content_id:
            logger.info(f"Attempt 4: Final try with stored content ID: {stored_id}")
            try:
                self.tv.art().select_image(stored_id)
                logger.info(f"Set fallback image ID: {stored_id} as active")
                return True
            except Exception as e:
                logger.warning(f"Stored ID fallback method failed: {e}")

        # Final desperate attempt: Send multiple select commands with delays
        try:
            logger.info("Final attempt: Sending multiple select commands with delays...")
            for attempt in range(3):
                try:
                    logger.info(f"Select attempt {attempt + 1}/3 for ID: {content_id}")
                    self.tv.art().select_image(content_id)
                    time.sleep(10)  # Wait between attempts
                except Exception as e:
                    logger.warning(f"Select attempt {attempt + 1} failed: {e}")
                    time.sleep(5)  # Shorter delay after failure
        except Exception as e:
            logger.warning(f"Multiple select commands approach failed: {e}")

        logger.error("All methods to set active art failed")
        return False

    def debug_tv_state(self) -> None:
        """Debug function to log detailed TV state information."""
        logger.info("=== TV DEBUG STATE ===")
        
        try:
            logger.info(f"TV IP: {self.tv_ip}")
            logger.info(f"TV available: {self.is_tv_available()}")
            
            # Log available art methods
            if hasattr(self.tv, 'art'):
                art_methods = [method for method in dir(self.tv.art()) if not method.startswith('_')]
                logger.info(f"Available art methods: {art_methods}")
            
            # Try to get device info
            if hasattr(self.tv, 'rest_device_info'):
                try:
                    device_info = self.tv.rest_device_info()
                    logger.info(f"Device info: {device_info}")
                except Exception as e:
                    logger.warning(f"Could not get device info: {e}")
            
            # Try to get art mode status
            try:
                if hasattr(self.tv.art(), 'get_artmode'):
                    artmode = self.tv.art().get_artmode()
                    logger.info(f"Art mode: {artmode}")
                else:
                    logger.info("Art mode status not available")
            except Exception as e:
                logger.warning(f"Could not get art mode: {e}")
            
            # Try to get content list
            try:
                content_list = None
                if hasattr(self.tv.art(), 'get_thumbnail_list'):
                    logger.debug("Trying get_thumbnail_list method...")
                    content_list = self.tv.art().get_thumbnail_list()
                elif hasattr(self.tv.art(), 'get_list'):
                    logger.debug("Trying get_list method...")
                    content_list = self.tv.art().get_list()
                elif hasattr(self.tv.art(), 'list'):
                    logger.debug("Trying list method...")
                    content_list = self.tv.art().list()
                else:
                    logger.warning("No content list method found")
                    
                if content_list:
                    logger.info(f"Content list length: {len(content_list)}")
                    for i, item in enumerate(content_list[:5]):
                        logger.info(f"Content {i+1}: {item}")
                else:
                    logger.info("Content list is empty or unavailable")
            except Exception as e:
                logger.warning(f"Could not get content list: {e}")
                logger.debug(f"Content list error details: {type(e).__name__}: {e}")
            
            # Try to get current image
            try:
                if hasattr(self.tv.art(), 'get_current'):
                    current = self.tv.art().get_current()
                    logger.info(f"Current image: {current}")
                else:
                    logger.info("Current image info not available")
            except Exception as e:
                logger.warning(f"Could not get current image: {e}")
                
        except Exception as e:
            logger.error(f"Debug state check failed: {e}")
        
        logger.info("=== END TV DEBUG STATE ===")
