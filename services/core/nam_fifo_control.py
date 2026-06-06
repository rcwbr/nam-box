"""
FIFO-based real-time control for NAM LV2 plugin.

This module allows sending model path changes to a modified jalv without
state file reloading, by writing to a Unix FIFO that jalv polls.

The jalv process must be modified to check the FIFO (see jalv_realtime_extension.c).
"""

import os
import threading
from pathlib import Path
from typing import Optional

# FIFO path for model control commands
MODEL_FIFO_PATH = Path(os.environ.get("MODEL_FIFO_PATH", "/var/nam/model_change.fifo"))


def ensure_fifo_exists(fifo_path: Path = MODEL_FIFO_PATH) -> bool:
    """Create the FIFO if it doesn't exist."""
    fifo_path.parent.mkdir(parents=True, exist_ok=True)

    if not fifo_path.exists():
        try:
            os.mkfifo(str(fifo_path))
            os.chmod(str(fifo_path), 0o666)
            return True
        except OSError as e:
            print(f"Failed to create FIFO: {e}")
            return False
    return True


def send_model_change(model_path: str) -> bool:
    """
    Send a model path change to jalv via FIFO.

    This function blocks until jalv reads the message (if jalv is running).
    If jalv is not running, it returns False.

    Args:
        model_path: Absolute path to the .nam model file

    Returns:
        True if message was sent successfully, False otherwise
    """
    fifo_path = MODEL_FIFO_PATH

    if not fifo_path.exists():
        print(f"FIFO not found at {fifo_path} - is jalv running with FIFO support?")
        return False

    try:
        # Open FIFO for writing (blocks until jalv opens for reading)
        with open(fifo_path, 'w') as f:
            f.write(model_path + '\n')
        return True
    except (OSError, IOError) as e:
        print(f"Failed to send model change: {e}")
        return False


def send_model_change_nonblocking(model_path: str, timeout: float = 1.0) -> bool:
    """
    Send a model path change to jalv via FIFO with timeout.

    Args:
        model_path: Absolute path to the .nam model file
        timeout: Maximum seconds to wait for jalv to read

    Returns:
        True if message was sent successfully, False on timeout/error
    """
    fifo_path = MODEL_FIFO_PATH
    if not fifo_path.exists():
        return False

    # Try to open with O_NONBLOCK
    try:
        fd = os.open(str(fifo_path), os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, (model_path + '\n').encode('utf-8'))
        os.close(fd)
        return True
    except BlockingIOError:
        # No reader available, jalv not running
        return False
    except OSError as e:
        print(f"Failed to send model change: {e}")
        return False


def set_model_and_notify(model_path: str, models_dir: Path = Path("/opt/nam/models")) -> dict:
    """
    Validate and send model change to jalv.

    This is the complete function to integrate with your API.
    """
    # Validate model exists
    if not model_path.startswith('/'):
        full_path = models_dir / model_path
    else:
        full_path = Path(model_path)

    if not full_path.exists():
        return {"status": "error", "message": f"Model not found: {model_path}"}

    # Ensure FIFO exists
    if not ensure_fifo_exists():
        return {"status": "error", "message": "Failed to create control FIFO"}

    # Send the path
    if send_model_change(str(full_path)):
        return {"status": "success", "model": str(full_path), "method": "fifo"}
    else:
        return {"status": "error", "message": "Failed to send model change - jalv may not be running with FIFO support"}


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python nam_fifo_control.py <model_path>")
        print("\nTo enable FIFO control, jalv must be patched with jalv_realtime_extension.c")
        sys.exit(1)

    result = set_model_and_notify(sys.argv[1])
    print(result)