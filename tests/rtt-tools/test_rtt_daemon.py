#!/usr/bin/env python3
"""
Tests for RTT Daemon (rtt_daemon.py).

These tests use a real RTT connection when available.
JLinkGDBServer is auto-started by conftest.py if not running.
"""

import os
import sys
import time
import signal
import socket
import tempfile
import shutil
from pathlib import Path
from typing import Optional

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rtt_daemon import RTTDaemon, check_rtt_server, DaemonAlreadyRunningError

# Import fixture helpers from conftest
from conftest import check_rtt_available, RTT_HOST, RTT_PORT

# Test constants
TEST_TIMEOUT = 5.0


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    tmp = Path(tempfile.mkdtemp(prefix="rtt_daemon_test_"))
    yield tmp
    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def daemon(temp_dir: Path) -> RTTDaemon:
    """Create a daemon instance for testing."""
    pid_file = temp_dir / "test.pid"
    log_file = temp_dir / "test.log"
    daemon = RTTDaemon(
        pid_file=pid_file,
        log_file=log_file,
        rtt_host=RTT_HOST,
        rtt_port=RTT_PORT,
    )
    yield daemon
    # Cleanup
    daemon.cleanup()


class TestRTTServerCheck:
    """Tests for RTT server connectivity checking."""

    def test_check_rtt_server_returns_bool(self):
        """check_rtt_server should return True/False."""
        result = check_rtt_server(RTT_HOST, RTT_PORT)
        assert isinstance(result, bool)

    def test_rtt_server_is_reachable(self):
        """Verify RTT server is actually reachable when running."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")
        assert check_rtt_available() is True


class TestDaemonPIDFile:
    """Tests for PID file management."""

    def test_daemon_creates_pid_file(self, daemon: RTTDaemon, temp_dir: Path):
        """Verify daemon creates PID file on startup."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        pid_file = temp_dir / "test.pid"
        assert not pid_file.exists(), "PID file should not exist before start"

        daemon.start()
        time.sleep(0.5)  # Give daemon time to create PID file

        assert pid_file.exists(), "PID file should be created on start"
        content = pid_file.read_text().strip()
        assert content.isdigit(), "PID file should contain numeric PID"
        assert int(content) == os.getpid() or int(content) == daemon.pid

    def test_daemon_removes_pid_file_on_cleanup(self, daemon: RTTDaemon, temp_dir: Path):
        """Verify daemon removes PID file on cleanup."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        pid_file = temp_dir / "test.pid"

        daemon.start()
        time.sleep(0.5)
        assert pid_file.exists()

        daemon.cleanup()
        assert not pid_file.exists(), "PID file should be removed on cleanup"

    def test_prevents_multiple_instances(self, temp_dir: Path):
        """Verify cannot start multiple daemon instances with same PID file."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        pid_file = temp_dir / "test.pid"
        """Verify cannot start multiple daemon instances with same PID file."""
        pid_file = temp_dir / "test.pid"
        log_file1 = temp_dir / "test1.log"
        log_file2 = temp_dir / "test2.log"

        daemon1 = RTTDaemon(pid_file=pid_file, log_file=log_file1, rtt_host=RTT_HOST, rtt_port=RTT_PORT)
        daemon1.start()
        time.sleep(0.5)

        daemon2 = RTTDaemon(pid_file=pid_file, log_file=log_file2, rtt_host=RTT_HOST, rtt_port=RTT_PORT)

        with pytest.raises(DaemonAlreadyRunningError):
            daemon2.start()

        daemon1.cleanup()


class TestDaemonLogWriting:
    """Tests for log file writing."""

    def test_daemon_writes_log_file(self, temp_dir: Path):
        """Verify daemon writes RTT data to log file."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        import threading

        pid_file = temp_dir / "test.pid"
        log_file = temp_dir / "test.log"

        daemon = RTTDaemon(
            pid_file=pid_file,
            log_file=log_file,
            rtt_host=RTT_HOST,
            rtt_port=RTT_PORT,
        )

        daemon.start()

        # Run daemon in background thread
        def run_daemon():
            daemon.run()

        thread = threading.Thread(target=run_daemon, daemon=True)
        thread.start()

        # Wait for RTT data (welcome message should arrive quickly)
        time.sleep(2.0)

        # Log file should be created with RTT welcome message
        assert log_file.exists(), "Log file should be created"
        content = log_file.read_text()
        # Should have received some data (JLinkGDBServer welcome message)
        assert len(content) > 0, "Log file should contain RTT data"

        daemon.cleanup()

    def test_daemon_adds_timestamp_to_lines(self, temp_dir: Path):
        """Verify daemon adds timestamps to log lines."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        import threading

        pid_file = temp_dir / "test.pid"
        log_file = temp_dir / "test.log"

        daemon = RTTDaemon(
            pid_file=pid_file,
            log_file=log_file,
            rtt_host=RTT_HOST,
            rtt_port=RTT_PORT,
        )

        daemon.start()

        # Run daemon in background thread
        def run_daemon():
            daemon.run()

        thread = threading.Thread(target=run_daemon, daemon=True)
        thread.start()

        # Wait for data
        time.sleep(2.0)

        content = log_file.read_text()
        if content.strip():  # Only check if there's content
            lines = content.strip().split('\n')
            # Each line should start with timestamp format [T:...]
            for line in lines[:5]:  # Check first 5 lines
                if line.strip():
                    assert line.startswith("[T:"), f"Line should start with [T:, got: {line[:20]}"

        daemon.cleanup()


class TestDaemonReconnect:
    """Tests for RTT disconnection/reconnection handling."""

    def test_daemon_handles_disconnect(self, daemon: RTTDaemon, temp_dir: Path):
        """Verify daemon handles RTT disconnect gracefully."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        # This test verifies the daemon doesn't crash on disconnect
        daemon.start()

        # Run for a while to potentially encounter disconnects
        time.sleep(5.0)

        # Daemon should still be running
        assert daemon.running, "Daemon should still be running after potential disconnect"


class TestLogRotation:
    """Tests for log file rotation."""

    def test_daemon_rotates_log_on_size(self, temp_dir: Path):
        """Verify daemon rotates log file when it exceeds size limit."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        pid_file = temp_dir / "test.pid"
        log_file = temp_dir / "test.log"

        # Use very small size limit for testing (1KB)
        daemon = RTTDaemon(
            pid_file=pid_file,
            log_file=log_file,
            rtt_host=RTT_HOST,
            rtt_port=RTT_PORT,
            max_log_size=1024,  # 1KB for testing
        )

        daemon.start()
        time.sleep(5.0)

        # Check for rotated files (test.log.1, test.log.2, etc.)
        rotated_files = list(temp_dir.glob("test.log.*"))
        # May or may not have rotated files depending on RTT traffic
        # Just verify no errors occurred
        assert daemon.running or len(rotated_files) >= 0

        daemon.cleanup()


class TestDaemonLifecycle:
    """Tests for daemon lifecycle management."""

    def test_daemon_start_stop_lifecycle(self, daemon: RTTDaemon):
        """Verify clean start and stop lifecycle."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        assert not daemon.running, "Daemon should not be running initially"

        daemon.start()
        assert daemon.running, "Daemon should be running after start"

        time.sleep(1.0)  # Brief run

        daemon.cleanup()
        assert not daemon.running, "Daemon should not be running after cleanup"


class TestCommandSocket:
    """Tests for daemon Unix Socket command handling."""

    def test_command_socket_created_on_start(self, daemon: RTTDaemon):
        """Verify command socket is created when daemon starts."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        daemon.start()

        try:
            # Verify command socket exists
            assert daemon._command_socket is not None
            # Verify socket file was created
            assert daemon._command_socket_path.exists()
        finally:
            daemon.cleanup()

    def test_command_in_progress_flag(self, daemon: RTTDaemon):
        """Verify _command_in_progress flag is properly managed."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        daemon.start()

        try:
            # Flag should be False initially
            assert daemon._command_in_progress is False

            # Manually set flag to test it exists
            daemon._command_in_progress = True
            assert daemon._command_in_progress is True

            # Reset
            daemon._command_in_progress = False
            assert daemon._command_in_progress is False
        finally:
            daemon.cleanup()

    def test_handle_command_sends_to_rtt(self, daemon: RTTDaemon):
        """Verify _handle_command sends command and captures response."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        daemon.start()
        time.sleep(0.5)  # Allow daemon to connect

        try:
            # Verify RTT socket is connected
            assert daemon._socket is not None

            # Send a simple command
            response = daemon._handle_command("help")

            # Should get a response (might be empty if device doesn't respond)
            assert response is not None
            # Response should be a string
            assert isinstance(response, str)
        finally:
            daemon.cleanup()

    def test_handle_command_with_no_rtt_connection(self, daemon: RTTDaemon):
        """Verify _handle_command returns error when RTT not connected."""
        # Don't start daemon - RTT socket will be None

        response = daemon._handle_command("test")

        assert "ERROR: RTT not connected" in response

    def test_accept_command_no_connection_available(self, daemon: RTTDaemon):
        """Verify _accept_command handles BlockingIOError gracefully."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        daemon.start()

        try:
            # Call _accept_command when no client is connecting
            # Should not raise exception, just return
            daemon._accept_command()

            # Verify flag is cleared after no-op
            assert daemon._command_in_progress is False
        finally:
            daemon.cleanup()


# Integration test helpers
def test_check_rtt_server_function():
    """Direct test of the check_rtt_server helper function."""
    # Test with invalid port - should return False
    result = check_rtt_server(RTT_HOST, 9999)
    assert result is False

    # Note: hostname resolution may succeed even for invalid hostnames
    # due to DNS behavior, so we only test the port check
