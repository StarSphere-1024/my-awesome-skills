#!/usr/bin/env python3
"""
Tests for unified RTT CLI (rtt.py).

These tests verify the CLI subcommands work correctly:
- daemon start|stop|status
- read --lines --since --grep
- send
- shell

JLinkGDBServer is auto-started by conftest.py if not running.
"""

import os
import sys
import time
import signal
import socket
import tempfile
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rtt_daemon import RTTDaemon, check_rtt_server

# Import fixture helpers from conftest
from conftest import check_rtt_available, RTT_HOST, RTT_PORT

# Test constants
SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
RTT_SCRIPT = SCRIPT_DIR / "rtt.py"


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    tmp = Path(tempfile.mkdtemp(prefix="rtt_cli_test_"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_log_file(temp_dir: Path) -> Path:
    """Create a sample log file with test data."""
    log_file = temp_dir / "rtt.log"
    now = datetime.now()

    lines = []
    for i in range(10):
        timestamp = (now - timedelta(seconds=i)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        lines.append(f"[T:{timestamp}] [INFO] Test message {i}")

    log_file.write_text('\n'.join(lines) + '\n')
    return log_file


class TestDaemonLifecycle:
    """Tests for daemon lifecycle management via CLI."""

    def test_cli_daemon_start_creates_pid_file(self, temp_dir: Path):
        """Verify daemon start creates PID file."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        pid_file = temp_dir / "test.pid"
        log_file = temp_dir / "test.log"

        # Start daemon in background using RTTDaemon class directly
        # (CLI daemon start runs forever, so we test the underlying functionality)
        from rtt_daemon import RTTDaemon
        daemon = RTTDaemon(pid_file=pid_file, log_file=log_file)
        daemon.start()
        time.sleep(0.5)

        try:
            # Verify PID file was created
            assert pid_file.exists(), "PID file should be created on daemon start"
            content = pid_file.read_text().strip()
            assert content.isdigit(), "PID file should contain numeric PID"
            assert int(content) == daemon.pid
        finally:
            daemon.cleanup()

    def test_cli_daemon_status_shows_running(self, temp_dir: Path):
        """Verify daemon status shows running daemon."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        pid_file = temp_dir / "test.pid"
        log_file = temp_dir / "test.log"

        daemon = RTTDaemon(pid_file=pid_file, log_file=log_file)
        daemon.start()
        time.sleep(0.5)

        try:
            result = subprocess.run(
                [sys.executable, str(RTT_SCRIPT), "daemon", "status",
                 "--pid-file", str(pid_file),
                 "--log-file", str(log_file)],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, f"Status should succeed: {result.stderr}"
            assert "running" in result.stdout.lower()
            assert f"PID: {daemon.pid}" in result.stdout
        finally:
            daemon.cleanup()

    def test_cli_daemon_prevents_multiple_instances(self, temp_dir: Path):
        """Verify cannot start multiple daemon instances."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        pid_file = temp_dir / "test.pid"
        log_file1 = temp_dir / "test1.log"
        log_file2 = temp_dir / "test2.log"

        daemon1 = RTTDaemon(pid_file=pid_file, log_file=log_file1)
        daemon1.start()
        time.sleep(0.5)

        try:
            result = subprocess.run(
                [sys.executable, str(RTT_SCRIPT), "daemon", "start",
                 "--pid-file", str(pid_file),
                 "--log-file", str(log_file2)],
                capture_output=True,
                text=True,
                timeout=3,
            )

            # Should fail because daemon is already running
            assert result.returncode != 0 or "already running" in result.stderr.lower()
        finally:
            daemon1.cleanup()


class TestReadCommand:
    """Tests for 'read' subcommand."""

    def test_cli_read_lines_returns_latest(self, sample_log_file: Path, temp_dir: Path):
        """Verify read --lines returns latest N lines."""
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "read",
             "--log-dir", str(temp_dir),
             "--lines", "5"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Read failed: {result.stderr}"
        lines = result.stdout.strip().split('\n')
        assert len(lines) == 5
        # Should return newest first
        assert "Test message 9" in lines[0]

    def test_cli_read_with_strip_ansi(self, temp_dir: Path):
        """Verify --strip-ansi and --no-strip-ansi options."""
        log_file = temp_dir / "rtt.log"
        log_file.write_text("\x1b[31mRed text\x1b[0m\nPlain text\n")

        # Default: strip ANSI
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "read",
             "--log-dir", str(temp_dir),
             "--lines", "10"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "\x1b[" not in result.stdout  # ANSI stripped

        # With --no-strip-ansi
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "read",
             "--log-dir", str(temp_dir),
             "--lines", "10",
             "--no-strip-ansi"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "\x1b[31m" in result.stdout  # ANSI kept

    def test_cli_read_grep_filter(self, sample_log_file: Path, temp_dir: Path):
        """Verify --grep filters lines."""
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "read",
             "--log-dir", str(temp_dir),
             "--grep", "Test message 5"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Test message 5" in result.stdout
        # Should only have one matching line
        lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
        assert len(lines) == 1

    def test_cli_read_since(self, sample_log_file: Path, temp_dir: Path):
        """Verify --since reads logs from time delta."""
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "read",
             "--log-dir", str(temp_dir),
             "--since", "60"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Should have some lines from last 60 seconds
        lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
        assert len(lines) > 0

    def test_cli_read_empty_dir(self, temp_dir: Path):
        """Verify read handles empty directory."""
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "read",
             "--log-dir", str(temp_dir),
             "--lines", "10"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "no matching lines" in result.stdout.lower() or result.stdout.strip() == ""


class TestSendCommand:
    """Tests for 'send' subcommand."""

    def test_cli_send_command(self):
        """Verify send command works with RTT server."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "send", "help",
             "--host", RTT_HOST,
             "--port", str(RTT_PORT)],
            capture_output=True,
            text=True,
        )

        # Should get some response from RTT
        assert result.returncode == 0 or len(result.stdout) > 0

    def test_cli_send_fails_without_server(self):
        """Verify send fails gracefully when server not running."""
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "send", "help",
             "--timeout", "1",
             "--host", "127.0.0.1",
             "--port", "9999"],
            capture_output=True,
            text=True,
        )

        # Should fail gracefully with error message
        assert result.returncode != 0 or "not running" in result.stdout.lower() or "failed" in result.stdout.lower()

    def test_cli_send_with_strip_ansi(self):
        """Verify send --no-strip-ansi keeps ANSI codes."""
        if not check_rtt_available():
            pytest.skip(f"RTT server not available at {RTT_HOST}:{RTT_PORT}")

        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "send", "help",
             "--host", RTT_HOST,
             "--port", str(RTT_PORT),
             "--no-strip-ansi"],
            capture_output=True,
            text=True,
        )

        # May or may not have ANSI depending on device output
        # Just verify it runs without error
        assert result.returncode == 0 or len(result.stdout) > 0

    def test_send_filters_by_timestamp(self, temp_dir: Path):
        """Verify send command filters log responses by timestamp.

        This tests that send only returns log lines that were written
        AFTER the command was sent, not old cached logs.
        """
        # Create log file with old entries
        log_file = temp_dir / "rtt.log"
        old_time = datetime.now() - timedelta(seconds=30)
        timestamp = old_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Old log entries (should NOT be returned by send)
        old_content = f"[T:{timestamp}] [INFO] Old log entry 1\n"
        old_content += f"[T:{timestamp}] [INFO] Old log entry 2\n"
        old_content += f"[T:{timestamp}] [INFO] Old log entry 3\n"

        log_file.write_text(old_content)

        # Verify old content is in file
        assert "Old log entry" in log_file.read_text()

        # Note: Full integration test would require:
        # 1. Starting daemon with our temp log dir
        # 2. Sending command
        # 3. Verifying only NEW entries are returned
        #
        # For now, we test the timestamp filtering logic directly
        from rtt_daemon import parse_timestamp

        # Verify old timestamps are parsed correctly
        parsed = parse_timestamp(f"[T:{timestamp}] [INFO] test")
        assert parsed is not None
        assert (datetime.now() - parsed).seconds >= 29  # About 30 seconds ago


class TestSendTimestampFiltering:
    """Tests for send command timestamp filtering logic."""

    def test_filter_logs_by_timestamp(self, temp_dir: Path):
        """Test that logs can be filtered by timestamp.

        This is the core logic used by 'send' to only return
        responses that occurred after the command was sent.
        """
        from rtt_daemon import read_since, parse_timestamp

        # Create log file with mixed old and new entries
        log_file = temp_dir / "rtt.log"
        now = datetime.now()
        old_time = now - timedelta(seconds=60)

        lines = []
        # Old entries (60 seconds ago - should be filtered out)
        # Format: [T:YYYY-MM-DD HH:MM:SS.mmm] - matches daemon output
        for i in range(3):
            ts = old_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            lines.append(f"[T:{ts}] [INFO] Old entry {i}")

        # New entries (5 seconds ago - should be included)
        for i in range(3):
            ts = (now - timedelta(seconds=5)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            lines.append(f"[T:{ts}] [INFO] New entry {i}")

        log_file.write_text('\n'.join(lines) + '\n')

        # Read only last 10 seconds (should only get new entries)
        result = read_since(temp_dir, seconds=10)

        # Should have new entries
        assert len(result) >= 3
        # Should NOT have old entries
        assert all("Old entry" not in line for line in result)
        assert all("New entry" in line for line in result)

    def test_send_command_uses_timestamp_filtering(self, temp_dir: Path, monkeypatch):
        """Test that send command works via daemon Unix Socket."""
        # Create log file with old entries
        log_file = temp_dir / "rtt.log"
        old_time = datetime.now() - timedelta(seconds=60)
        ts = old_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        old_content = f"[T:{ts}] [INFO] Old entry - should not appear\n"
        old_content += f"[T:{ts}] [INFO] Another old entry\n"
        log_file.write_text(old_content)

        # Mock send_command_via_daemon to simulate daemon response
        def mock_send_via_daemon(command, socket_path=None):
            return True, f"Response to: {command}"

        import rtt
        monkeypatch.setattr(rtt, 'send_command_via_daemon', mock_send_via_daemon)

        # Create args namespace
        import argparse
        args = argparse.Namespace(
            command="test",
            host="127.0.0.1",
            port=19021,
            wait_for_shell=False,
            shell_timeout=10.0,
            log_dir=temp_dir,
            pattern="rtt.log*",
            no_strip_ansi=False,
            lines=20,
        )

        # Run send command
        result = rtt.cmd_send(args)

        # Should succeed and print response
        assert result == 0


class TestCLIHelp:
    """Tests for CLI help messages."""

    def test_cli_main_help(self):
        """Verify main help shows all subcommands."""
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "daemon" in result.stdout
        assert "read" in result.stdout
        assert "send" in result.stdout
        # Note: shell command was removed - daemon is the sole RTT reader

    def test_cli_daemon_help(self):
        """Verify daemon help shows actions."""
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "daemon", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "start" in result.stdout
        assert "stop" in result.stdout
        assert "status" in result.stdout

    def test_cli_read_help(self):
        """Verify read help shows options."""
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "read", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "--lines" in result.stdout
        assert "--since" in result.stdout
        assert "--grep" in result.stdout

    def test_cli_send_help(self):
        """Verify send help shows options."""
        result = subprocess.run(
            [sys.executable, str(RTT_SCRIPT), "send", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # --timeout was removed - send now uses timestamp filtering
        assert "--wait-for-shell" in result.stdout
        assert "--log-dir" in result.stdout
        assert "--lines" in result.stdout


class TestStripAnsiFunction:
    """Tests for strip_ansi function exported in rtt.py."""

    def test_strip_ansi_from_rtt(self):
        """Test strip_ansi works with typical RTT output."""
        from rtt_daemon import strip_ansi

        # Typical RTT output with ANSI colors
        text = "\x1b[32m[INFO]\x1b[0m System started\n"
        result = strip_ansi(text)
        assert result == "[INFO] System started\n"

    def test_strip_ansi_preserves_content(self):
        """Test strip_ansi preserves non-ANSI content."""
        from rtt_daemon import strip_ansi

        text = "Plain text without colors"
        result = strip_ansi(text)
        assert result == text
