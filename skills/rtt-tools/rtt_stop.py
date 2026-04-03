#!/usr/bin/env python3
"""
J-Link RTT Server Stopper - Stop background JLinkGDBServer process.

This script reads the PID file created by rtt_start.py --keep-alive
and terminates the JLinkGDBServer process gracefully.

Usage:
    python rtt_stop.py                      # Stop using default PID file
    python rtt_stop.py --pid-file-dir /path  # Use custom PID file directory
"""

import os
import sys
import argparse
import signal
from pathlib import Path
from typing import Optional


# Default PID file directory (matches rtt_start.py)
DEFAULT_PID_FILE_DIR = Path.home() / ".rtt_tools"
PID_FILE_NAME = "gdb_server.pid"


def get_pid_file(pid_file_dir: Optional[Path] = None) -> Path:
    """Get the full path to the PID file."""
    if pid_file_dir is None:
        pid_file_dir = DEFAULT_PID_FILE_DIR
    return pid_file_dir / PID_FILE_NAME


def read_pid_file(pid_file: Path) -> Optional[int]:
    """
    Read PID from file.

    Args:
        pid_file: Path to PID file

    Returns:
        PID as integer, or None if file doesn't exist or is invalid
    """
    if not pid_file.exists():
        return None
    try:
        content = pid_file.read_text().strip()
        return int(content)
    except (ValueError, IOError) as e:
        print(f"Error reading PID file: {e}", file=sys.stderr)
        return None


def remove_pid_file(pid_file: Path) -> None:
    """
    Remove PID file after stopping process.

    Args:
        pid_file: Path to PID file
    """
    if pid_file.exists():
        try:
            pid_file.unlink()
        except IOError as e:
            print(f"Warning: Could not remove PID file: {e}", file=sys.stderr)


def stop_process(pid: int) -> bool:
    """
    Send SIGTERM to process and wait for it to exit.

    Args:
        pid: Process ID to stop

    Returns:
        True if process was stopped, False otherwise
    """
    try:
        # Check if process exists
        os.kill(pid, 0)
    except ProcessLookupError:
        print(f"Process {pid} is not running (already exited?)")
        return False
    except PermissionError:
        print(f"Process {pid} exists but no permission to signal it")
        return False

    try:
        # Send SIGTERM for graceful shutdown
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to process {pid}")

        # Wait for process to exit (up to 5 seconds)
        for _ in range(50):  # 50 * 0.1s = 5s
            try:
                os.kill(pid, 0)
                import time
                time.sleep(0.1)
            except ProcessLookupError:
                print(f"Process {pid} terminated successfully")
                return True

        # Process didn't exit gracefully, send SIGKILL
        print(f"Process {pid} did not exit gracefully, sending SIGKILL...")
        os.kill(pid, signal.SIGKILL)
        return True

    except ProcessLookupError:
        print(f"Process {pid} exited before we could signal it")
        return True
    except PermissionError:
        print(f"Error: No permission to send signal to process {pid}")
        return False
    except OSError as e:
        print(f"Error sending signal to process {pid}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Stop background JLinkGDBServer process",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Stop using default PID file location
  %(prog)s --pid-file-dir /custom   # Use custom PID file directory

Note: This command only works when JLinkGDBServer was started with
      rtt_start.py --keep-alive.
        """,
    )

    parser.add_argument(
        "--pid-file-dir",
        type=Path,
        default=None,
        help=f"Directory containing PID file (default: {DEFAULT_PID_FILE_DIR})",
    )

    args = parser.parse_args()

    # Get PID file path
    pid_file = get_pid_file(args.pid_file_dir)

    # Read PID from file
    pid = read_pid_file(pid_file)
    if pid is None:
        print(
            f"Error: PID file not found at {pid_file}\n"
            f"Make sure JLinkGDBServer was started with --keep-alive option.",
            file=sys.stderr
        )
        sys.exit(1)

    print(f"Found JLinkGDBServer process with PID: {pid}")

    # Stop the process
    success = stop_process(pid)

    # Clean up PID file
    if success:
        remove_pid_file(pid_file)
        print(f"JLinkGDBServer stopped successfully")
        sys.exit(0)
    else:
        # Still try to clean up PID file even if process wasn't found
        remove_pid_file(pid_file)
        sys.exit(1)


if __name__ == "__main__":
    main()
