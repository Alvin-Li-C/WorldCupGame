"""Compatibility shims for cursor-sdk on Python < 3.12 (Windows)."""
import os


def ensure_cursor_sdk_os_compat():
    """cursor-sdk bridge uses os.get_blocking / set_blocking (added in 3.12)."""
    if hasattr(os, 'get_blocking'):
        return

    def get_blocking(fd):
        return True

    def set_blocking(fd, blocking):
        pass

    os.get_blocking = get_blocking  # type: ignore[attr-defined]
    os.set_blocking = set_blocking  # type: ignore[attr-defined]
