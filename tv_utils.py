#!/usr/bin/env python3
"""Shared utilities for Samsung TV operations."""

import logging
import socket
from contextlib import contextmanager
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


@contextmanager
def websocket_timeout_patch(timeout_seconds: float) -> Iterator[None]:
    """Context manager to temporarily patch WebSocket timeout.

    The samsungtvws library has a hardcoded 5-second WebSocket timeout which
    causes 'ms.channel.timeOut' errors. This patches socket.settimeout to use
    a longer timeout instead.

    Args:
        timeout_seconds: The minimum timeout to use in seconds. Any timeout
            less than this will be overridden.

    Yields:
        None

    Example:
        with websocket_timeout_patch(300):
            # All socket operations will use at least 300 second timeout
            tv.art().upload(data)
    """
    original_settimeout: Optional[Any] = None
    patch_applied = False

    try:
        # Store original settimeout function
        original_settimeout = socket.socket.settimeout

        # Create patched version that uses our minimum timeout
        def patched_settimeout(sock_self: Any, timeout: Any) -> Any:
            # Override any timeout less than our configured timeout
            if timeout is not None and timeout < timeout_seconds:
                logger.debug(
                    f"Overriding socket timeout from {timeout}s "
                    f"to {timeout_seconds}s"
                )
                timeout = timeout_seconds
            return original_settimeout(sock_self, timeout)

        # Apply the patch
        socket.socket.settimeout = patched_settimeout  # type: ignore
        patch_applied = True
        logger.debug(
            f"Applied WebSocket timeout patch for {timeout_seconds}s"
        )

        yield

    except Exception as e:
        logger.warning(f"Error during WebSocket timeout patch: {e}")
        raise

    finally:
        # Restore original function
        if patch_applied and original_settimeout is not None:
            try:
                socket.socket.settimeout = original_settimeout  # type: ignore
                logger.debug("Restored original socket.settimeout function")
            except Exception as e:
                logger.debug(
                    f"Error restoring socket timeout (non-critical): {e}"
                )


def calculate_upload_timeout(file_size_mb: float, base_timeout: float = 300.0) -> float:
    """Calculate appropriate upload timeout based on file size.

    Args:
        file_size_mb: File size in megabytes.
        base_timeout: Base timeout in seconds (default: 300).

    Returns:
        Calculated timeout in seconds (max of base_timeout or file_size_mb * 5).
    """
    calculated_timeout = max(base_timeout, file_size_mb * 5)
    logger.debug(
        f"Calculated timeout for {file_size_mb:.2f}MB file: "
        f"{calculated_timeout}s"
    )
    return calculated_timeout
