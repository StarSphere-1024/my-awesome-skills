#!/usr/bin/env python3
"""
Tests for exported helper functions from rtt_daemon.py.

These tests verify the exported helper functions work correctly:
- strip_ansi()
- read_lines()
- read_since()
- grep_lines()
- list_log_files()
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rtt_daemon import (
    strip_ansi,
    read_lines,
    read_since,
    grep_lines,
    list_log_files,
    parse_timestamp,
)


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    tmp = Path(tempfile.mkdtemp(prefix="rtt_helpers_test_"))
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

    # Write oldest first, newest last
    log_file.write_text('\n'.join(lines) + '\n')
    return log_file


class TestStripAnsi:
    """Tests for strip_ansi function."""

    def test_strip_ansi_colors(self):
        """Test stripping ANSI color codes."""
        text = "\x1b[31mRed text\x1b[0m"
        result = strip_ansi(text)
        assert result == "Red text"

    def test_strip_ansi_cursor_movement(self):
        """Test stripping ANSI cursor movement."""
        text = "Hello\x1b[2J\x1b[HWorld"
        result = strip_ansi(text)
        assert result == "HelloWorld"

    def test_strip_ansi_no_codes(self):
        """Test text without ANSI codes passes through."""
        text = "Plain text without codes"
        result = strip_ansi(text)
        assert result == text

    def test_strip_ansi_empty_string(self):
        """Test empty string."""
        result = strip_ansi("")
        assert result == ""

    def test_strip_ansi_complex_sequence(self):
        """Test complex ANSI sequences."""
        text = "\x1b[1;31;42mBold Red on Green\x1b[0m"
        result = strip_ansi(text)
        assert result == "Bold Red on Green"


class TestReadLines:
    """Tests for read_lines function."""

    def test_read_latest_n_lines(self, sample_log_file: Path, temp_dir: Path):
        """Test reading the latest N lines."""
        lines = read_lines(temp_dir, 5)
        assert len(lines) == 5
        # Should return newest first
        assert "Test message 9" in lines[0]
        assert "Test message 5" in lines[-1]

    def test_read_all_lines(self, sample_log_file: Path, temp_dir: Path):
        """Test reading all lines."""
        lines = read_lines(temp_dir, 100)
        assert len(lines) == 10

    def test_read_from_empty_dir(self, temp_dir: Path):
        """Test reading from empty directory."""
        lines = read_lines(temp_dir, 10)
        assert len(lines) == 0

    def test_read_from_nonexistent_dir(self):
        """Test reading from non-existent directory."""
        lines = read_lines(Path("/nonexistent/path"), 10)
        assert len(lines) == 0

    def test_read_with_custom_pattern(self, temp_dir: Path):
        """Test reading with custom file pattern."""
        log_file = temp_dir / "custom.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\n")

        lines = read_lines(temp_dir, 10, pattern="custom.log")
        assert len(lines) == 3


class TestReadSince:
    """Tests for read_since function."""

    def test_read_since_recent_time(self, sample_log_file: Path, temp_dir: Path):
        """Test reading logs since recent time."""
        lines = read_since(temp_dir, 5)
        # Should have some lines from last 5 seconds
        assert len(lines) <= 10
        assert len(lines) > 0

    def test_read_since_old_time(self, sample_log_file: Path, temp_dir: Path):
        """Test reading logs since old time (should return all)."""
        lines = read_since(temp_dir, 3600)  # 1 hour ago
        assert len(lines) == 10

    def test_read_since_empty_dir(self, temp_dir: Path):
        """Test reading since time from empty directory."""
        lines = read_since(temp_dir, 60)
        assert len(lines) == 0


class TestGrepLines:
    """Tests for grep_lines function."""

    def test_grep_exact_match(self, sample_log_file: Path, temp_dir: Path):
        """Test grep with exact pattern match."""
        lines = grep_lines(temp_dir, "Test message 5")
        assert len(lines) == 1
        assert "Test message 5" in lines[0]

    def test_grep_regex_match(self, sample_log_file: Path, temp_dir: Path):
        """Test grep with regex pattern."""
        lines = grep_lines(temp_dir, r"message [0-2]$", regex=True)
        # Should match: message 0, message 1, message 2
        assert len(lines) == 3

    def test_grep_no_match(self, sample_log_file: Path, temp_dir: Path):
        """Test grep with no matching pattern."""
        lines = grep_lines(temp_dir, "NONEXISTENT_PATTERN")
        assert len(lines) == 0

    def test_grep_case_insensitive(self, temp_dir: Path):
        """Test case-insensitive grep."""
        log_file = temp_dir / "rtt.log"  # Use default pattern name
        content = "[T:2024-01-01 00:00:00.000] [INFO] HELLO\n"
        content += "[T:2024-01-01 00:00:01.000] [INFO] hello\n"
        log_file.write_text(content)

        lines = grep_lines(temp_dir, "hello", case_sensitive=False)
        assert len(lines) == 2

    def test_grep_invalid_regex(self, sample_log_file: Path, temp_dir: Path):
        """Test grep with invalid regex returns empty."""
        lines = grep_lines(temp_dir, "[invalid(regex", regex=True)
        assert len(lines) == 0


class TestListLogFiles:
    """Tests for list_log_files function."""

    def test_list_log_files(self, temp_dir: Path):
        """Test listing log files."""
        # Create multiple log files
        for i in range(3):
            log_file = temp_dir / f"rtt.log.{i}"
            log_file.write_text(f"Log {i}\n")

        files = list_log_files(temp_dir, "rtt.log*")
        assert len(files) == 3

    def test_list_log_files_sorted(self, temp_dir: Path):
        """Test that log files are sorted by modification time."""
        base = temp_dir / "rtt.log"
        for i in range(3):
            f = base.parent / f"{base.name}.{i}"
            f.write_text(f"Log {i}\n")
            # Set different modification times
            old_time = time.time() - (i * 100)
            os.utime(f, (old_time, old_time))

        files = list_log_files(temp_dir, "rtt.log*")
        # Should be sorted by mtime (newest first)
        assert len(files) == 3
        # Verify sorted (newest first means smallest i should be last)
        for i in range(len(files) - 1):
            assert files[i][1] >= files[i + 1][1]

    def test_list_log_files_empty_dir(self, temp_dir: Path):
        """Test listing log files in empty directory."""
        files = list_log_files(temp_dir, "nonexistent*")
        assert len(files) == 0

    def test_list_log_files_nonexistent_dir(self):
        """Test listing log files in non-existent directory."""
        files = list_log_files(Path("/nonexistent/path"))
        assert len(files) == 0


class TestParseTimestamp:
    """Tests for parse_timestamp function."""

    def test_parse_valid_timestamp(self):
        """Test parsing a valid timestamp."""
        line = "[T:2024-01-15 10:30:45.123] [INFO] Some message"
        ts = parse_timestamp(line)
        assert ts is not None
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15
        assert ts.hour == 10
        assert ts.minute == 30
        assert ts.second == 45
        assert ts.microsecond == 123000

    def test_parse_invalid_timestamp(self):
        """Test parsing an invalid timestamp."""
        line = "No timestamp here"
        ts = parse_timestamp(line)
        assert ts is None

    def test_parse_malformed_timestamp(self):
        """Test parsing a malformed timestamp."""
        line = "[T:invalid-date] [INFO] Message"
        ts = parse_timestamp(line)
        assert ts is None
