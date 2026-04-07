#!/usr/bin/env python3
"""
Pytest configuration and fixtures for RTT tools tests.

This module provides fixtures for:
- Auto-starting JLinkGDBServer if not running
- Cleaning up server after tests
"""

import os
import sys
import time
import socket
import subprocess
import signal
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from rtt_daemon import check_rtt_server, DEFAULT_PID_FILE_DIR

# Test constants
RTT_HOST = "127.0.0.1"
RTT_PORT = 19021
GDB_PORT = 2331

# Device for testing - can be overridden via environment variable
TEST_DEVICE = os.environ.get("RTT_TEST_DEVICE", "nRF52840_XXAA")


def check_rtt_available() -> bool:
    """Check if RTT server is reachable."""
    return check_rtt_server(RTT_HOST, RTT_PORT)


def check_gdb_server_available() -> bool:
    """Check if JLinkGDBServer is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex((RTT_HOST, GDB_PORT))
        sock.close()
        return result == 0
    except socket.error:
        return False


def get_gdb_server_pid() -> int:
    """Get JLinkGDBServer PID from PID file."""
    pid_file = DEFAULT_PID_FILE_DIR / "gdb_server.pid"
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text().strip())
    except (ValueError, IOError):
        return None


def start_gdb_server(device: str = TEST_DEVICE) -> bool:
    """
    Start JLinkGDBServer in background.

    Returns:
        True if started successfully, False otherwise
    """
    cmd = [
        "JLinkGDBServer",
        "-device", device,
        "-if", "SWD",
        "-speed", "4000",
        "-port", str(GDB_PORT),
        "-rttport", str(RTT_PORT),
        "-single",
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

        # Wait for server to initialize
        time.sleep(3)

        if proc.poll() is not None:
            print(f"\nFailed to start JLinkGDBServer (device={device})")
            return False

        # Write PID file
        pid_file = DEFAULT_PID_FILE_DIR / "gdb_server.pid"
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(proc.pid))

        print(f"\nStarted JLinkGDBServer (PID: {proc.pid}, device: {device})")
        return True

    except FileNotFoundError:
        print(f"\nJLinkGDBServer not found. Please install J-Link software.")
        return False
    except Exception as e:
        print(f"\nError starting JLinkGDBServer: {e}")
        return False


def stop_gdb_server() -> bool:
    """Stop JLinkGDBServer using PID file."""
    pid = get_gdb_server_pid()
    if pid is None:
        return False

    pid_file = DEFAULT_PID_FILE_DIR / "gdb_server.pid"

    try:
        os.kill(pid, 0)  # Check if process exists
    except ProcessLookupError:
        if pid_file.exists():
            pid_file.unlink()
        return False

    print(f"\nStopping JLinkGDBServer (PID: {pid})...")
    os.kill(pid, signal.SIGTERM)

    # Wait for graceful shutdown
    for _ in range(50):
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except ProcessLookupError:
            print("JLinkGDBServer stopped")
            if pid_file.exists():
                pid_file.unlink()
            return True

    # Force kill
    print("Sending SIGKILL...")
    os.kill(pid, signal.SIGKILL)
    time.sleep(0.5)
    if pid_file.exists():
        pid_file.unlink()
    return True


@pytest.fixture(scope="session", autouse=True)
def rtt_server_session():
    """
    Session-scoped fixture to ensure JLinkGDBServer is running.

    If server is already running, do nothing.
    If not running, try to start it.
    Clean up after all tests complete.
    """
    server_started = False

    # Check if already running
    if not check_rtt_available():
        print(f"\nRTT server not available at {RTT_HOST}:{RTT_PORT}")
        print(f"Attempting to start JLinkGDBServer with device: {TEST_DEVICE}")

        if start_gdb_server(TEST_DEVICE):
            server_started = True
            # Wait a bit more for RTT to be ready
            time.sleep(2)
        else:
            print(f"\nFailed to start JLinkGDBServer. Tests requiring RTT will be skipped.")
    else:
        print(f"\nRTT server already running at {RTT_HOST}:{RTT_PORT}")

    yield

    # Cleanup: stop server if we started it
    if server_started:
        stop_gdb_server()


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    import tempfile
    import shutil

    tmp = Path(tempfile.mkdtemp(prefix="rtt_test_"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)
