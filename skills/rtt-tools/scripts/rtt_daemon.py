#!/usr/bin/env python3
"""
J-Link RTT Daemon - Background daemon for continuous RTT log capture.

This daemon continuously reads from the J-Link RTT telnet port and writes
output to a rotating log file. It manages its own PID file for process
supervision and supports automatic log rotation.

Usage:
    python rtt_daemon.py --device nRF52840_XXAA   # Start daemon
    python rtt_daemon.py --stop                    # Stop running daemon

Features:
- Automatic PID file management
- Log file rotation (size and time based)
- RTT reconnection with exponential backoff
- Signal handling (SIGTERM, SIGINT)
- File locking for safe concurrent writes
"""

import os
import sys
import socket
import signal
import fcntl
import argparse
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass


# Default configuration constants
DEFAULT_PID_FILE_DIR = Path.home() / ".rtt_tools"
DEFAULT_LOG_DIR = Path.home() / ".rtt_tools" / "logs"
DEFAULT_RTT_HOST = "127.0.0.1"
DEFAULT_RTT_PORT = 19021
DEFAULT_RTT_TIMEOUT = 5.0
DEFAULT_MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
DEFAULT_MAX_LOG_AGE = 24 * 60 * 60  # 24 hours
DEFAULT_ROTATION_COUNT = 10  # Keep last 10 rotated files
RECONNECT_BACKOFF_BASE = 1.0  # Base delay for exponential backoff
MAX_RECONNECT_BACKOFF = 30.0  # Maximum reconnect delay

# Unix Socket for command channel
DEFAULT_COMMAND_SOCKET = Path.home() / ".rtt_tools" / "rtt_command.sock"
COMMAND_TIMEOUT = 5.0  # Timeout for command execution
SOCKET_BUFFER_SIZE = 4096


class DaemonAlreadyRunningError(Exception):
    """Raised when trying to start a daemon that's already running."""
    pass


class RTTConnectionError(Exception):
    """Raised when RTT connection fails."""
    pass


def check_rtt_server(host: str, port: int) -> bool:
    """
    Check if RTT server is reachable.

    Args:
        host: RTT server hostname
        port: RTT server port

    Returns:
        True if server is reachable, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.error:
        return False


def format_timestamp() -> str:
    """Format current time as timestamp string for log lines."""
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    return f"[T:{timestamp}]"


def parse_timestamp(line: str) -> Optional[datetime]:
    """
    Parse timestamp from a log line.

    Args:
        line: Log line starting with [T:timestamp]

    Returns:
        datetime object or None if parsing fails
    """
    match = re.match(r'\[T:([^\]]+)\]', line)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return None


@dataclass
class DaemonConfig:
    """Configuration for RTT Daemon."""
    pid_file: Path
    log_file: Path
    rtt_host: str = DEFAULT_RTT_HOST
    rtt_port: int = DEFAULT_RTT_PORT
    rtt_timeout: float = DEFAULT_RTT_TIMEOUT
    max_log_size: int = DEFAULT_MAX_LOG_SIZE
    max_log_age: int = DEFAULT_MAX_LOG_AGE
    rotation_count: int = DEFAULT_ROTATION_COUNT


class RTTDaemon:
    """
    RTT Daemon for continuous log capture.

    Continuously reads from J-Link RTT telnet port and writes to a rotating
    log file. Manages PID file for process supervision.

    Attributes:
        config: Daemon configuration
        running: Whether daemon is currently running
        pid: Process ID of daemon
        socket: RTT socket connection
    """

    def __init__(
        self,
        pid_file: Optional[Path] = None,
        log_file: Optional[Path] = None,
        rtt_host: str = DEFAULT_RTT_HOST,
        rtt_port: int = DEFAULT_RTT_PORT,
        rtt_timeout: float = DEFAULT_RTT_TIMEOUT,
        max_log_size: int = DEFAULT_MAX_LOG_SIZE,
        max_log_age: int = DEFAULT_MAX_LOG_AGE,
    ):
        """
        Initialize RTT Daemon.

        Args:
            pid_file: Path to PID file (default: ~/.rtt_tools/rtt_daemon.pid)
            log_file: Path to log file (default: ~/.rtt_tools/logs/rtt.log)
            rtt_host: RTT server hostname
            rtt_port: RTT server port
            rtt_timeout: Socket timeout for RTT reads
            max_log_size: Maximum log file size before rotation
            max_log_age: Maximum log file age before rotation
        """
        # Set up paths
        if pid_file is None:
            pid_file = DEFAULT_PID_FILE_DIR / "rtt_daemon.pid"
        if log_file is None:
            log_file = DEFAULT_LOG_DIR / "rtt.log"

        self.config = DaemonConfig(
            pid_file=pid_file,
            log_file=log_file,
            rtt_host=rtt_host,
            rtt_port=rtt_port,
            rtt_timeout=rtt_timeout,
            max_log_size=max_log_size,
            max_log_age=max_log_age,
        )

        self.running = False
        self.pid = os.getpid()
        self._socket: Optional[socket.socket] = None
        self._reconnect_attempts = 0
        self._last_reconnect_time = 0.0

        # Command socket for Unix Socket communication
        self._command_socket: Optional[socket.socket] = None
        self._command_socket_path = DEFAULT_COMMAND_SOCKET

        # Flag to prevent RTT reading while command is being processed
        self._command_in_progress = False

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle termination signals."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False

    def _check_existing_daemon(self) -> None:
        """
        Check if another daemon instance is already running.

        Raises:
            DaemonAlreadyRunningError: If another instance is running
        """
        pid_file = self.config.pid_file
        if not pid_file.exists():
            return

        try:
            content = pid_file.read_text().strip()
            existing_pid = int(content)
        except (ValueError, IOError):
            # Invalid PID file, will overwrite
            return

        # Check if process is actually running
        try:
            os.kill(existing_pid, 0)
            # Process exists
            raise DaemonAlreadyRunningError(
                f"Daemon already running with PID {existing_pid}. "
                f"PID file: {pid_file}"
            )
        except ProcessLookupError:
            # Process not running, stale PID file
            pid_file.unlink()

    def _write_pid_file(self) -> None:
        """Write PID file."""
        self.config.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.pid_file.write_text(str(self.pid))

    def _remove_pid_file(self) -> None:
        """Remove PID file."""
        if self.config.pid_file.exists():
            self.config.pid_file.unlink()

    def _connect_rtt(self) -> None:
        """
        Connect to RTT server.

        Raises:
            RTTConnectionError: If connection fails
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.config.rtt_timeout)
            self._socket.connect((self.config.rtt_host, self.config.rtt_port))
            self._reconnect_attempts = 0
        except socket.error as e:
            self._socket = None
            raise RTTConnectionError(
                f"Failed to connect to RTT at {self.config.rtt_host}:{self.config.rtt_port}: {e}"
            )

    def _reconnect_rtt(self) -> bool:
        """
        Attempt to reconnect to RTT server with exponential backoff.

        Returns:
            True if reconnection successful, False otherwise
        """
        now = time.time()
        backoff = min(
            RECONNECT_BACKOFF_BASE * (2 ** self._reconnect_attempts),
            MAX_RECONNECT_BACKOFF
        )

        # Check if enough time has passed since last attempt
        if now - self._last_reconnect_time < backoff:
            return False

        self._last_reconnect_time = now
        self._reconnect_attempts += 1

        try:
            self._disconnect_rtt()
            self._connect_rtt()
            print(f"RTT reconnected (attempt {self._reconnect_attempts})")
            return True
        except RTTConnectionError:
            if self._reconnect_attempts >= 3:
                print(f"RTT reconnection failed after {self._reconnect_attempts} attempts")
            return False

    def _disconnect_rtt(self) -> None:
        """Disconnect from RTT server."""
        if self._socket:
            try:
                self._socket.close()
            except socket.error:
                pass
            self._socket = None

    def _setup_command_socket(self) -> None:
        """
        Set up Unix Socket for receiving commands.
        """
        # Remove existing socket file
        if self._command_socket_path.exists():
            self._command_socket_path.unlink()

        # Create Unix Socket
        self._command_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._command_socket.bind(str(self._command_socket_path))
        self._command_socket.listen(5)
        self._command_socket.setblocking(False)
        print(f"Command socket listening at {self._command_socket_path}")

    def _handle_command(self, command: str) -> str:
        """
        Send command to RTT and return response.

        Args:
            command: Command string to send

        Returns:
            Response from RTT
        """
        if not self._socket:
            return "ERROR: RTT not connected"

        try:
            # Send command
            self._socket.sendall((command + "\n").encode("utf-8"))

            # Read response with timeout
            response_buffer = []
            start_time = time.time()

            while (time.time() - start_time) < COMMAND_TIMEOUT:
                try:
                    data = self._socket.recv(SOCKET_BUFFER_SIZE)
                    if data:
                        text = data.decode("utf-8", errors="replace")
                        response_buffer.append(text)
                        # Give device time to respond
                        time.sleep(0.1)
                    else:
                        break
                except socket.timeout:
                    break
                except BlockingIOError:
                    time.sleep(0.05)

            # Also write to log
            if response_buffer:
                full_response = "".join(response_buffer)
                self._write_log(f"[CMD] {command}\n[RESPONSE] {full_response}".encode("utf-8"))
                return full_response
            else:
                self._write_log(f"[CMD] {command}\n[RESPONSE] (no response)".encode("utf-8"))
                return "(no response)"

        except Exception as e:
            return f"ERROR: {e}"

    def _accept_command(self) -> None:
        """
        Accept and process a command from Unix Socket.
        """
        if not self._command_socket:
            return

        try:
            client, _ = self._command_socket.accept()
            client.settimeout(COMMAND_TIMEOUT)

            # Set flag to pause main loop RTT reading
            self._command_in_progress = True

            try:
                # Read command
                command = client.recv(SOCKET_BUFFER_SIZE).decode("utf-8").strip()

                if command:
                    # Execute command and send response
                    response = self._handle_command(command)
                    client.sendall(response.encode("utf-8"))

                client.close()

            finally:
                # Clear flag to resume main loop RTT reading
                self._command_in_progress = False

        except BlockingIOError as e:
            # Expected for non-blocking socket - no connection waiting
            # Debug: verify this is being called
            pass
        except socket.timeout:
            pass
        except Exception as e:
            # This should NOT be called for BlockingIOError
            # Debug: print type to verify
            print(f"DEBUG: Exception type={type(e).__name__}, args={e.args}", file=sys.stderr)
            print(f"Command handling error: {e}", file=sys.stderr)
            # Clear flag even on error
            self._command_in_progress = False

    def _read_rtt(self) -> Optional[bytes]:
        """
        Read data from RTT socket.

        Returns:
            Bytes data if available, None if no data or error
        """
        if not self._socket:
            return None

        try:
            data = self._socket.recv(4096)
            return data if data else None
        except socket.timeout:
            return None
        except socket.error:
            return None

    def _write_log(self, data: bytes) -> None:
        """
        Write data to log file with file locking.

        Args:
            data: Raw bytes to write
        """
        # Decode with error handling
        text = data.decode("utf-8", errors="replace")

        # Add timestamp to each line
        timestamp = format_timestamp()
        lines = text.split('\n')
        timestamped_lines = []
        for line in lines:
            if line.strip():
                timestamped_lines.append(f"{timestamp} {line}")
            else:
                timestamped_lines.append(line)

        content = '\n'.join(timestamped_lines) + '\n'

        # Ensure log directory exists
        self.config.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Write with file locking
        try:
            with open(self.config.log_file, 'a') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(content)
                    f.flush()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except IOError as e:
            print(f"Error writing to log file: {e}", file=sys.stderr)

    def _check_rotate(self) -> bool:
        """
        Check if log file needs rotation and rotate if necessary.

        Returns:
            True if rotation occurred, False otherwise
        """
        log_file = self.config.log_file

        if not log_file.exists():
            return False

        try:
            stat = log_file.stat()
        except OSError:
            return False

        should_rotate = False
        now = time.time()

        # Check size
        if stat.st_size > self.config.max_log_size:
            should_rotate = True

        # Check age
        file_age = now - stat.st_mtime
        if file_age > self.config.max_log_age:
            should_rotate = True

        if not should_rotate:
            return False

        # Perform rotation
        return self._rotate_log()

    def _rotate_log(self) -> bool:
        """
        Rotate log file by renaming with numeric suffix.

        Returns:
            True if rotation successful, False otherwise
        """
        log_file = self.config.log_file

        try:
            # Find existing rotated files
            base_name = log_file.name
            parent_dir = log_file.parent

            # Get list of rotated files
            rotated = []
            for f in parent_dir.glob(f"{base_name}.*"):
                if f.is_file():
                    match = re.match(rf'{re.escape(base_name)}\.(\d+)', f.name)
                    if match:
                        rotated.append((int(match.group(1)), f))

            # Sort by number
            rotated.sort(key=lambda x: x[0])

            # Delete oldest files if exceeding rotation count
            while len(rotated) >= self.config.rotation_count:
                _, oldest = rotated.pop(0)
                try:
                    oldest.unlink()
                except OSError:
                    pass

            # Shift existing files
            for num, f in reversed(rotated):
                new_num = num + 1
                if new_num <= self.config.rotation_count:
                    new_path = parent_dir / f"{base_name}.{new_num}"
                    try:
                        f.rename(new_path)
                    except OSError:
                        pass

            # Rotate current file to .1
            rotated_path = parent_dir / f"{base_name}.1"
            log_file.rename(rotated_path)

            print(f"Rotated log file: {log_file} -> {rotated_path}")
            return True

        except OSError as e:
            print(f"Error rotating log file: {e}", file=sys.stderr)
            return False

    def _cleanup_old_logs(self) -> None:
        """Remove old rotated log files beyond retention policy."""
        log_file = self.config.log_file
        base_name = log_file.name
        parent_dir = log_file.parent

        now = time.time()

        for f in parent_dir.glob(f"{base_name}.*"):
            if f.is_file():
                # Check file age
                try:
                    file_age = now - f.stat().st_mtime
                    if file_age > self.config.max_log_age:
                        f.unlink()
                        print(f"Removed old log file: {f}")
                except OSError:
                    pass

    def start(self) -> None:
        """
        Start the daemon.

        Raises:
            DaemonAlreadyRunningError: If another instance is already running
        """
        # Check for existing daemon
        self._check_existing_daemon()

        # Write PID file
        self._write_pid_file()

        # Clean up old logs
        self._cleanup_old_logs()

        # Set up command socket
        self._setup_command_socket()

        # Connect to RTT
        try:
            self._connect_rtt()
            print(f"Connected to RTT at {self.config.rtt_host}:{self.config.rtt_port}")
        except RTTConnectionError as e:
            print(f"Warning: {e}", file=sys.stderr)
            print("Will attempt to reconnect...")

        self.running = True

    def run(self) -> None:
        """
        Run the daemon main loop.

        Call start() before this method.
        """
        if not self.running:
            raise RuntimeError("Daemon not started. Call start() first.")

        print(f"RTT daemon started (PID: {self.pid})")
        print(f"Logging to: {self.config.log_file}")

        try:
            while self.running:
                # Check for log rotation
                if self._check_rotate():
                    continue

                # Check for incoming commands (non-blocking)
                try:
                    self._accept_command()
                except BlockingIOError:
                    pass

                # Read from RTT only when no command is being processed
                # This prevents race condition where main loop reads response
                # before _handle_command() can capture it
                if self._socket and not self._command_in_progress:
                    data = self._read_rtt()
                    if data:
                        self._write_log(data)
                elif not self._socket:
                    # Try to reconnect
                    if not self._reconnect_rtt():
                        time.sleep(1.0)
                        continue

                # Brief sleep to prevent busy waiting
                time.sleep(0.1)

        except Exception as e:
            print(f"Daemon error: {e}", file=sys.stderr)
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up resources and stop daemon."""
        self.running = False

        # Disconnect RTT
        self._disconnect_rtt()

        # Close and remove command socket
        if self._command_socket:
            try:
                self._command_socket.close()
            except socket.error:
                pass
        if self._command_socket_path.exists():
            try:
                self._command_socket_path.unlink()
            except OSError:
                pass

        # Remove PID file
        self._remove_pid_file()

        print("RTT daemon stopped")


def main():
    """Main entry point for daemon CLI."""
    parser = argparse.ArgumentParser(
        description="J-Link RTT background daemon for continuous log capture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start                          # Start daemon with defaults
  %(prog)s --start --device nRF52840_XXAA   # Start with device hint
  %(prog)s --stop                           # Stop running daemon
  %(prog)s --status                         # Check daemon status
  %(prog)s --log-file /path/to/log          # Custom log file location

Note: The daemon writes RTT output to ~/.rtt_tools/logs/rtt.log by default.
      Use 'python rtt_log.py' to read and query the log files.
        """
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--start",
        action="store_true",
        help="Start the RTT daemon"
    )
    group.add_argument(
        "--stop",
        action="store_true",
        help="Stop the running daemon"
    )
    group.add_argument(
        "--status",
        action="store_true",
        help="Check daemon status"
    )
    group.add_argument(
        "--restart",
        action="store_true",
        help="Restart the daemon"
    )

    parser.add_argument(
        "--pid-file",
        type=Path,
        default=None,
        help="Path to PID file (default: ~/.rtt_tools/rtt_daemon.pid)"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to log file (default: ~/.rtt_tools/logs/rtt.log)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_RTT_HOST,
        help=f"RTT server hostname (default: {DEFAULT_RTT_HOST})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_RTT_PORT,
        help=f"RTT server port (default: {DEFAULT_RTT_PORT})"
    )
    parser.add_argument(
        "--max-log-size",
        type=int,
        default=DEFAULT_MAX_LOG_SIZE,
        help=f"Max log file size in bytes before rotation (default: {DEFAULT_MAX_LOG_SIZE})"
    )
    parser.add_argument(
        "--max-log-age",
        type=int,
        default=DEFAULT_MAX_LOG_AGE,
        help=f"Max log file age in seconds before rotation (default: {DEFAULT_MAX_LOG_AGE}s)"
    )

    args = parser.parse_args()

    daemon = RTTDaemon(
        pid_file=args.pid_file,
        log_file=args.log_file,
        rtt_host=args.host,
        rtt_port=args.port,
        max_log_size=args.max_log_size,
        max_log_age=args.max_log_age,
    )

    if args.start:
        if args.status:
            # Check status before starting
            pid_file = daemon.config.pid_file
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    os.kill(pid, 0)
                    print(f"Daemon already running with PID {pid}")
                    sys.exit(0)
                except (ValueError, ProcessLookupError):
                    pid_file.unlink()
            print("Daemon not running (will start)")

        try:
            daemon.start()
            daemon.run()
        except DaemonAlreadyRunningError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nInterrupted")
            daemon.cleanup()
            sys.exit(0)

    elif args.stop:
        pid_file = daemon.config.pid_file
        if not pid_file.exists():
            print("Daemon is not running (no PID file)")
            sys.exit(1)

        try:
            pid = int(pid_file.read_text().strip())
        except ValueError:
            print("Error: Invalid PID file")
            sys.exit(1)

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            print("Daemon is not running (stale PID file)")
            pid_file.unlink()
            sys.exit(1)

        print(f"Stopping daemon (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)

        # Wait for daemon to stop
        for _ in range(50):
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                print("Daemon stopped")
                sys.exit(0)

        print("Daemon did not stop gracefully, sending SIGKILL...")
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)
        pid_file.unlink()
        print("Daemon stopped")
        sys.exit(0)

    elif args.status:
        pid_file = daemon.config.pid_file
        if not pid_file.exists():
            print("Daemon is not running")
            sys.exit(1)

        try:
            pid = int(pid_file.read_text().strip())
        except ValueError:
            print("Error: Invalid PID file")
            sys.exit(1)

        try:
            os.kill(pid, 0)
            print(f"Daemon is running (PID: {pid})")
            print(f"PID file: {pid_file}")
            print(f"Log file: {daemon.config.log_file}")
            sys.exit(0)
        except ProcessLookupError:
            print("Daemon is not running (stale PID file)")
            pid_file.unlink()
            sys.exit(1)

    elif args.restart:
        # Stop existing daemon
        pid_file = daemon.config.pid_file
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)
                print(f"Stopping existing daemon (PID: {pid})...")
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
            except (ValueError, ProcessLookupError):
                pass

        # Start new daemon
        try:
            daemon.start()
            daemon.run()
        except DaemonAlreadyRunningError:
            print("Error: Could not restart daemon")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nInterrupted")
            daemon.cleanup()
            sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()


# ============================================================================
# Exported Helper Functions (for rtt.py and external use)
# ============================================================================

def strip_ansi(text: str) -> str:
    """
    Remove ANSI escape sequences (colors, cursor control) from text.

    Args:
        text: Text containing ANSI escape sequences

    Returns:
        Text with ANSI sequences removed
    """
    ansi_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_pattern.sub("", text)


def read_lines(log_dir: Path, n: int, pattern: str = "rtt.log*") -> List[str]:
    """
    Read latest N lines from log files.

    Args:
        log_dir: Directory containing log files
        n: Number of lines to read
        pattern: Glob pattern for log files (default: rtt.log*)

    Returns:
        List of the latest N lines (chronological order - oldest first)
    """
    all_lines = []
    files = list_log_files(log_dir, pattern)

    for file_path, _ in files:
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.strip().split('\n')
            all_lines.extend(lines)
        except (IOError, UnicodeDecodeError):
            continue

    if not all_lines:
        return []

    # Take last N lines (chronological order - oldest first)
    latest = all_lines[-n:] if len(all_lines) >= n else all_lines
    return latest


def read_since(log_dir: Path, seconds: int, pattern: str = "rtt.log*") -> List[str]:
    """
    Read logs since N seconds ago.

    Args:
        log_dir: Directory containing log files
        seconds: Number of seconds ago to read from
        pattern: Glob pattern for log files (default: rtt.log*)

    Returns:
        List of matching log lines (chronological order - oldest first)
    """
    cutoff = datetime.now() - timedelta(seconds=seconds)
    all_lines = []
    files = list_log_files(log_dir, pattern)

    for file_path, _ in files:
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.strip().split('\n')
            all_lines.extend(lines)
        except (IOError, UnicodeDecodeError):
            continue

    matching = []
    for line in all_lines:
        ts = parse_timestamp(line)
        if ts and ts >= cutoff:
            matching.append(line)
        elif not ts:
            # Include lines without timestamp
            matching.append(line)

    return matching


def grep_lines(
    log_dir: Path,
    pattern: str,
    case_sensitive: bool = True,
    regex: bool = False,
    log_pattern: str = "rtt.log*"
) -> List[str]:
    """
    Grep for pattern in log files.

    Args:
        log_dir: Directory containing log files
        pattern: Pattern to search for
        case_sensitive: Case-sensitive search (default: True)
        regex: Use regex matching (default: False)
        log_pattern: Glob pattern for log files (default: rtt.log*)

    Returns:
        List of matching lines (chronological order - oldest first)
    """
    all_lines = []
    files = list_log_files(log_dir, log_pattern)

    for file_path, _ in files:
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.strip().split('\n')
            all_lines.extend(lines)
        except (IOError, UnicodeDecodeError):
            continue

    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            compiled = re.compile(pattern, flags)
        except re.error:
            return []
        matching = [line for line in all_lines if compiled.search(line)]
    else:
        if case_sensitive:
            matching = [line for line in all_lines if pattern in line]
        else:
            pattern_lower = pattern.lower()
            matching = [line for line in all_lines if pattern_lower in line.lower()]

    return matching


def list_log_files(
    log_dir: Path,
    pattern: str = "rtt.log*"
) -> List[Tuple[Path, float]]:
    """
    List all log files matching pattern, sorted by modification time.

    Args:
        log_dir: Directory to search
        pattern: Glob pattern for log files (default: rtt.log*)

    Returns:
        List of (path, mtime) tuples, sorted by mtime (newest first)
    """
    if not log_dir.exists():
        return []

    files = []
    for f in log_dir.glob(pattern):
        if f.is_file():
            try:
                mtime = f.stat().st_mtime
                files.append((f, mtime))
            except OSError:
                continue

    # Sort by modification time (newest first)
    files.sort(key=lambda x: x[1], reverse=True)
    return files
