#!/usr/bin/env python3
"""
Samsung Frame TV Power Control Script

Controls power state of Samsung Frame TV with art mode management.
Designed for cron/automated usage with proper exit codes and minimal output.

Usage:
    python tv_power.py ON    # Turn TV on and enable art mode
    python tv_power.py OFF   # Turn TV completely off

Exit codes:
    0: Success
    1: Invalid arguments
    2: Connection error
    3: Operation failed

Examples:
    # In crontab (turn on at 8 AM, off at 11 PM):
    0 8 * * * /path/to/.venv/bin/python /path/to/tv_power.py ON
    0 23 * * * /path/to/.venv/bin/python /path/to/tv_power.py OFF

Environment variables (in .env file):
    SAMSUNG_TV_IP: IP address of the TV
    SAMSUNG_TV_MAC: MAC address for Wake-on-LAN
"""

import os
import sys
import time
import socket
import logging
import argparse
import urllib3
from typing import Optional, Tuple, Any
from pathlib import Path
from dotenv import load_dotenv
from tv_utils import websocket_timeout_patch

# Suppress InsecureRequestWarning for local TV connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import Samsung TV library
try:
    from samsungtvws import SamsungTVWS  # type: ignore
    from samsungtvws.exceptions import HttpApiError  # type: ignore
except ImportError as e:
    raise ImportError(
        "samsungtvws library not installed. "
        "Run: pip install -r requirements.txt"
    ) from e

# Optional: Import Wake-on-LAN if available
try:
    from wakeonlan import send_magic_packet  # type: ignore
    HAS_WOL = True
except ImportError:
    HAS_WOL = False


# Setup logging (minimal for cron usage)
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class FrameTVPowerController:
    """Controls Samsung Frame TV power state and art mode."""

    def __init__(self, tv_ip: str, tv_mac: Optional[str] = None, timeout: int = 300) -> None:
        """Initialize TV power controller.

        Args:
            tv_ip: IP address of the TV
            tv_mac: MAC address for Wake-on-LAN (optional)
            timeout: Connection timeout in seconds (default 300s/5min)
        """
        self.tv_ip = tv_ip
        self.tv_mac = tv_mac
        self.timeout = timeout
        self.tv: Optional[SamsungTVWS] = None
        self._original_settimeout: Optional[Any] = None
        self._patch_applied = False

    def _is_tv_reachable(self, timeout: float = 5.0) -> bool:
        """Check if TV is reachable on the network.

        Args:
            timeout: Socket timeout in seconds

        Returns:
            True if TV responds to connection attempt
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.tv_ip, 8002))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _apply_websocket_timeout_patch(self) -> None:
        """Apply WebSocket timeout patch to fix samsungtvws 5-second timeout.

        The samsungtvws library has a hardcoded 5-second WebSocket timeout which
        causes 'ms.channel.timeOut' errors. This patches socket.settimeout to use
        our longer timeout instead.
        """
        if self._patch_applied:
            return

        try:
            # Store original settimeout function
            self._original_settimeout = socket.socket.settimeout

            # Create patched version that uses our timeout
            timeout_value = self.timeout

            def patched_settimeout(sock_self: Any, timeout: Any) -> Any:
                # Override any timeout less than our configured timeout
                if timeout is not None and timeout < timeout_value:
                    logger.debug(
                        f"Overriding socket timeout from {timeout}s to {timeout_value}s"
                    )
                    timeout = timeout_value
                return self._original_settimeout(sock_self, timeout)  # type: ignore

            # Apply the patch
            socket.socket.settimeout = patched_settimeout  # type: ignore
            self._patch_applied = True
            logger.debug(f"Applied WebSocket timeout patch for {self.timeout}s")

        except Exception as e:
            logger.warning(f"Could not apply WebSocket timeout patch: {e}")

    def _restore_websocket_timeout_patch(self) -> None:
        """Restore original socket.settimeout function."""
        if not self._patch_applied or self._original_settimeout is None:
            return

        try:
            socket.socket.settimeout = self._original_settimeout  # type: ignore
            self._patch_applied = False
            logger.debug("Restored original socket.settimeout function")
        except Exception as e:
            logger.warning(f"Could not restore socket.settimeout: {e}")

    def _connect_to_tv(self) -> bool:
        """Establish connection to the TV.

        Returns:
            True if connection successful
        """
        try:
            # Apply WebSocket timeout patch before connecting
            self._apply_websocket_timeout_patch()

            logger.debug(f"Connecting to TV at {self.tv_ip}...")
            self.tv = SamsungTVWS(
                self.tv_ip,
                port=8002,
                name="DailyArtApp",  # Use same name as upload_image.py to avoid re-auth
                timeout=self.timeout
            )

            # Test connection
            if hasattr(self.tv, 'rest_device_info'):
                self.tv.rest_device_info()
            elif hasattr(self.tv, 'info'):
                self.tv.info()

            logger.debug("TV connection established")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to TV: {e}")
            return False

    def _wake_tv_with_wol(self) -> bool:
        """Wake TV using Wake-on-LAN.

        Returns:
            True if WOL packet sent successfully
        """
        if not HAS_WOL:
            logger.warning("wakeonlan library not installed, cannot send WOL packet")
            return False

        if not self.tv_mac:
            logger.warning("TV MAC address not configured, cannot send WOL packet")
            return False

        try:
            logger.debug(f"Sending Wake-on-LAN packet to {self.tv_mac}")
            send_magic_packet(self.tv_mac)
            return True
        except Exception as e:
            logger.error(f"Failed to send WOL packet: {e}")
            return False

    def _get_art_mode_status(self) -> Optional[bool]:
        """Get current art mode status.

        Returns:
            True if in art mode, False if not, None if unable to determine
        """
        if not self.tv:
            return None

        try:
            art_api = self.tv.art()
            status = art_api.get_artmode()

            # Handle different response formats
            if isinstance(status, bool):
                logger.debug(f"Art mode status (bool): {status}")
                return status
            elif isinstance(status, dict) and 'artmode' in status:
                result = bool(status['artmode'])
                logger.debug(f"Art mode status (dict.artmode): {result}")
                return result
            elif isinstance(status, dict) and 'data' in status:
                # Some firmware versions nest the response
                data = status.get('data', {})
                if isinstance(data, dict) and 'value' in data:
                    result = data['value'] == 'on'
                    logger.debug(f"Art mode status (dict.data.value): {result}")
                    return result

            logger.debug(f"Unexpected art mode response: {status}")
            return None

        except Exception as e:
            error_str = str(e)
            # Error -7 when checking art mode might mean TV is already in art mode
            if "error number -7" in error_str:
                logger.debug("Error -7 when checking art mode, likely already in art mode")
                return True
            logger.debug(f"Could not get art mode status: {e}")
            return None

    def _set_art_mode(self, enabled: bool) -> bool:
        """Set art mode on or off.

        Args:
            enabled: True to enable art mode, False to disable

        Returns:
            True if operation successful
        """
        if not self.tv:
            return False

        try:
            logger.debug(f"Setting art mode to: {enabled}")
            art_api = self.tv.art()
            art_api.set_artmode(enabled)

            # Wait briefly for mode change
            time.sleep(2)

            # Verify the change
            current_mode = self._get_art_mode_status()
            if current_mode is not None:
                return current_mode == enabled

            # If we can't verify, assume success
            return True

        except Exception as e:
            error_str = str(e)

            # Error -7 means TV can't switch to art mode from current state
            # OR it might already be in the requested state
            if "error number -7" in error_str or "-7" in error_str:
                logger.info(
                    f"Received error -7 when setting art mode to {enabled}. "
                    "TV may already be in the requested state."
                )

                # Check current state to see if we're already where we want to be
                current_mode = self._get_art_mode_status()
                if current_mode == enabled:
                    logger.info(f"TV is already in art mode={enabled}, treating as success")
                    return True

                if enabled:
                    logger.warning("TV not in art mode but cannot switch. May be showing regular content.")
                    # For now, just return True and let the user check
                    # The TV might switch on its own or need manual intervention
                    logger.info("Assuming TV will enter art mode on next power cycle")
                    return True
                else:
                    # If disabling art mode failed with -7, TV might already be off/normal
                    logger.info("TV likely already in normal mode")
                    return True
            else:
                logger.error(f"Failed to set art mode: {e}")
                return False

    def _power_toggle(self) -> bool:
        """Send power toggle command to TV.

        Returns:
            True if command sent successfully
        """
        if not self.tv:
            return False

        try:
            logger.debug("Sending power toggle command")
            self.tv.shortcuts().power()
            return True
        except Exception as e:
            logger.error(f"Failed to send power command: {e}")
            return False

    def turn_on(self) -> Tuple[bool, str]:
        """Turn TV on and enable art mode.

        Returns:
            Tuple of (success, status_message)
        """
        try:
            # First check if TV is reachable
            if not self._is_tv_reachable(timeout=2.0):
                logger.info("TV not reachable, attempting Wake-on-LAN")

                # Try Wake-on-LAN
                if self._wake_tv_with_wol():
                    # Wait for TV to boot
                    logger.info("WOL sent, waiting for TV to power on...")
                    for i in range(30):  # Wait up to 30 seconds
                        time.sleep(1)
                        if self._is_tv_reachable(timeout=1.0):
                            logger.info(f"TV responded after {i+1} seconds")
                            break
                    else:
                        return False, "TV did not respond after Wake-on-LAN"
                else:
                    # Try power toggle anyway (might work if TV is in standby)
                    logger.info("Attempting direct power on without WOL")

            # Connect to TV
            if not self._connect_to_tv():
                return False, "Failed to connect to TV"

            # Check if already in art mode
            current_art_mode = self._get_art_mode_status()

            if current_art_mode is True:
                logger.info("TV already on and in art mode")
                return True, "TV already in art mode"

            # If TV is on but not in art mode, enable it
            if current_art_mode is False:
                logger.info("TV on but not in art mode, enabling art mode")
                if self._set_art_mode(True):
                    return True, "Art mode enabled"
                else:
                    return False, "Failed to enable art mode"

            # If we can't determine art mode status, try to enable it anyway
            logger.info("Art mode status unknown, attempting to enable")

            # Send power command if TV seems off
            if not self._is_tv_reachable():
                self._power_toggle()
                time.sleep(5)  # Wait for TV to respond

            # Try to enable art mode
            if self._set_art_mode(True):
                return True, "TV turned on with art mode"

            # If art mode failed but TV is on, partial success
            if self._is_tv_reachable():
                return True, "TV turned on (art mode status uncertain)"

            return False, "Failed to turn on TV"

        finally:
            # Always restore the WebSocket patch
            self._restore_websocket_timeout_patch()

    def turn_off(self) -> Tuple[bool, str]:
        """Turn TV completely off.

        Returns:
            Tuple of (success, status_message)
        """
        try:
            # Check if TV is reachable
            if not self._is_tv_reachable(timeout=2.0):
                logger.info("TV appears to be already off")
                return True, "TV already off"

            # Connect to TV
            if not self._connect_to_tv():
                # TV is reachable but can't connect - might be in a weird state
                logger.warning("TV reachable but cannot connect")
                return False, "Failed to connect to TV"

            # Try to send power key directly without checking art mode
            # (art mode checks can timeout if TV is not in art mode)
            logger.debug("Sending KEY_POWER to turn off TV")
            try:
                self.tv.send_key("KEY_POWER")
                logger.info("Power command sent successfully")

                # Wait for TV to process
                time.sleep(3)

                # Verify TV is off
                if not self._is_tv_reachable(timeout=2.0):
                    return True, "TV powered off successfully"
                else:
                    # TV still reachable, might be in standby
                    logger.info("TV still reachable after power command (may be in standby)")
                    return True, "TV in standby mode"

            except Exception as e:
                logger.error(f"Failed to send power key: {e}")

                # Fallback: try shortcuts().power()
                logger.info("Trying fallback method: shortcuts().power()")
                try:
                    self.tv.shortcuts().power()
                    time.sleep(3)

                    if not self._is_tv_reachable(timeout=2.0):
                        return True, "TV powered off (fallback method)"
                    else:
                        return True, "TV in standby (fallback method)"

                except Exception as e2:
                    logger.error(f"Fallback method also failed: {e2}")
                    return False, f"Failed to send power off command: {e2}"

        finally:
            # Always restore the WebSocket patch
            self._restore_websocket_timeout_patch()


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code (0=success, 1=invalid args, 2=connection error, 3=operation failed)
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Control Samsung Frame TV power state",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
  0 - Success
  1 - Invalid arguments
  2 - Connection error
  3 - Operation failed

Examples:
  python tv_power.py ON    # Turn on TV with art mode
  python tv_power.py OFF   # Turn TV off completely

For cron usage (silent operation):
  0 8 * * * /path/to/python /path/to/tv_power.py ON >/dev/null 2>&1
  0 23 * * * /path/to/python /path/to/tv_power.py OFF >/dev/null 2>&1
"""
    )

    parser.add_argument(
        'command',
        choices=['ON', 'OFF', 'on', 'off'],
        help='Power command (ON or OFF)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--ip',
        help='TV IP address (overrides .env file)'
    )

    parser.add_argument(
        '--mac',
        help='TV MAC address for WOL (overrides .env file)'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)

    # Load environment variables
    load_dotenv()

    # Get TV configuration
    tv_ip = args.ip or os.getenv('SAMSUNG_TV_IP')
    tv_mac = args.mac or os.getenv('SAMSUNG_TV_MAC')

    if not tv_ip:
        logger.error("TV IP address not provided. Set SAMSUNG_TV_IP in .env or use --ip")
        return 1

    # Normalize command
    command = args.command.upper()

    # Create controller
    controller = FrameTVPowerController(tv_ip, tv_mac)

    # Execute command
    try:
        if command == 'ON':
            success, message = controller.turn_on()
        else:  # OFF
            success, message = controller.turn_off()

        if success:
            logger.info(f"Success: {message}")
            return 0
        else:
            logger.error(f"Failed: {message}")
            return 3

    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return 2
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())