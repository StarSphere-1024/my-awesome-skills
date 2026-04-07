#!/usr/bin/env python3
"""
J-Link RTT Tools - Unified CLI Entry Point

A complete toolset for interacting with SEGGER J-Link RTT (Real-Time Transfer) streams.

Subcommands:
  daemon  - Manage background RTT log capture daemon
  server  - Start/stop JLinkGDBServer (provides RTT on port 19021)
  read    - Read and query RTT log files
  send    - Send command to device and read response
  shell   - Interactive shell session

Usage:
  python rtt.py server start -d <device>     # Start JLinkGDBServer
  python rtt.py daemon start                 # Start RTT daemon
  python rtt.py read --lines 50              # Read logs
  python rtt.py send "command"               # Send command
  python rtt.py shell                        # Interactive shell
"""

import os
import sys
import socket
import signal
import argparse
import time
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

# Import helper functions from rtt_daemon
from rtt_daemon import (
    RTTDaemon,
    DaemonAlreadyRunningError,
    DEFAULT_PID_FILE_DIR,
    DEFAULT_LOG_DIR,
    DEFAULT_RTT_HOST,
    DEFAULT_RTT_PORT,
    strip_ansi,
    read_lines,
    read_since,
    grep_lines,
    list_log_files,
    parse_timestamp,
    DEFAULT_COMMAND_SOCKET,
    COMMAND_TIMEOUT,
)


# Default configuration constants
DEFAULT_TIMEOUT = 3
DEFAULT_LINES = 50
DEFAULT_SHELL_TIMEOUT = 10.0
DEFAULT_GDB_PORT = 2331
DEFAULT_RTT_PORT = 19021
DEFAULT_SPEED = 4000
DEFAULT_INTERFACE = "SWD"
GDB_SERVER_PID_FILE = DEFAULT_PID_FILE_DIR / "gdb_server.pid"
SHELL_PROMPT_PATTERN = re.compile(rb"rtt:~\$|\[0m\[[0-9;]*mrtt:~\$|zephyr.*>|\(zephyr\).*#")


# ============================================================================
# Helper Functions
# ============================================================================

def wait_for_shell_prompt(data: bytes, timeout: float = 10.0) -> bool:
    """
    Check if shell prompt is detected in data stream.

    Args:
        data: Raw bytes received from RTT stream
        timeout: Not used in this synchronous version - kept for API compatibility

    Returns:
        True if prompt detected, False otherwise
    """
    return bool(SHELL_PROMPT_PATTERN.search(data))


def read_rtt(
    timeout: int = 3,
    command: str = None,
    host: str = DEFAULT_RTT_HOST,
    port: int = DEFAULT_RTT_PORT,
    strip_ansi_codes: bool = True,
    wait_for_shell: bool = False,
    shell_timeout: float = DEFAULT_SHELL_TIMEOUT,
) -> str:
    """
    Connect to J-Link RTT, optionally send a command, and capture logs.

    Args:
        timeout: How many seconds to listen for RTT output (default: 3)
        command: Optional Zephyr Shell command to send before reading
        host: RTT server hostname (default: 127.0.0.1)
        port: RTT server port (default: 19021)
        strip_ansi_codes: Remove ANSI escape sequences from output (default: True)
        wait_for_shell: Wait for shell prompt before sending command (default: False)
        shell_timeout: Timeout for waiting for shell prompt in seconds (default: 10)

    Returns:
        Captured RTT output as a string, or error message if connection fails
    """
    output_lines = []

    try:
        # Create socket and set timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.setblocking(1)

        # Attempt connection
        try:
            sock.connect((host, port))
        except ConnectionRefusedError:
            return "J-Link RTT server is not running on port 19021. Please ensure JLinkExe is connected to the target."
        except socket.timeout:
            return f"Connection to {host}:{port} timed out after {timeout}s."
        except OSError as e:
            return f"Failed to connect to RTT server at {host}:{port}: {e}"

        # If wait_for_shell is enabled, wait for shell prompt before sending command
        shell_detected = False
        if wait_for_shell and command:
            sock.setblocking(0)  # Non-blocking for shell detection
            start_time = time.time()
            shell_buffer = b""

            while (time.time() - start_time) < shell_timeout:
                try:
                    data = sock.recv(4096)
                    if data:
                        shell_buffer += data
                        if wait_for_shell_prompt(shell_buffer):
                            shell_detected = True
                            # Decode and add to output
                            text = shell_buffer.decode("utf-8", errors="replace")
                            if strip_ansi_codes:
                                text = strip_ansi(text)
                            output_lines.append(text)
                            break
                except BlockingIOError:
                    time.sleep(0.05)
                except socket.timeout:
                    break

            if not shell_detected:
                warning = f"\nWarning: Shell prompt not detected within {shell_timeout}s, sending command anyway...\n"
                output_lines.append(warning)
            else:
                # Shell detected, clear the buffer for fresh command output
                output_lines.clear()

            # Switch back to blocking mode for command sending
            sock.setblocking(1)

        # Send command if provided
        if command:
            command_with_newline = command + "\n"
            try:
                sock.sendall(command_with_newline.encode("utf-8"))
                time.sleep(0.2)  # Wait for device to process
            except socket.error as e:
                sock.close()
                return f"Failed to send command: {e}"

        # Read loop with timeout
        start_time = time.time()
        sock.setblocking(0)  # Non-blocking for read loop

        while (time.time() - start_time) < timeout:
            try:
                data = sock.recv(4096)
                if data:
                    text = data.decode("utf-8", errors="replace")
                    if strip_ansi_codes:
                        text = strip_ansi(text)
                    output_lines.append(text)
            except BlockingIOError:
                time.sleep(0.05)
            except socket.timeout:
                break

        sock.close()
        return "".join(output_lines)

    except Exception as e:
        return f"Unexpected error reading RTT: {e}"


def check_rtt_server(host: str = DEFAULT_RTT_HOST, port: int = DEFAULT_RTT_PORT) -> bool:
    """Check if RTT server is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.error:
        return False


def check_gdb_server(host: str = DEFAULT_RTT_HOST, port: int = DEFAULT_GDB_PORT) -> bool:
    """Check if JLinkGDBServer is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.error:
        return False


def start_gdb_server(
    device: str,
    speed: int = DEFAULT_SPEED,
    interface: str = DEFAULT_INTERFACE,
    gdb_port: int = DEFAULT_GDB_PORT,
    rtt_port: int = DEFAULT_RTT_PORT,
    keep_alive: bool = True,
) -> tuple[bool, Optional[int]]:
    """
    Start JLinkGDBServer in background.

    Args:
        device: Target device (e.g., nRF52840_XXAA)
        speed: J-Link speed in kHz (default: 4000)
        interface: Interface type SWD or JTAG (default: SWD)
        gdb_port: GDB server port (default: 2331)
        rtt_port: RTT server port (default: 19021)
        keep_alive: Run in background and create PID file (default: True)

    Returns:
        Tuple of (success, pid or None)
    """
    cmd = [
        "JLinkGDBServer",
        "-device", device,
        "-if", interface,
        "-speed", str(speed),
        "-port", str(gdb_port),
        "-rttport", str(rtt_port),
        "-single",
    ]

    print(f"Starting JLinkGDBServer (device={device}, if={interface}, speed={speed})...")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

        # Wait for server to initialize
        time.sleep(2)

        if proc.poll() is not None:
            print("Error: JLinkGDBServer failed to start.")
            return False, None

        if keep_alive:
            # Write PID file
            GDB_SERVER_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
            GDB_SERVER_PID_FILE.write_text(str(proc.pid))
            print(f"JLinkGDBServer started (PID: {proc.pid})")
            print(f"PID file: {GDB_SERVER_PID_FILE}")
            print(f"RTT available at {DEFAULT_RTT_HOST}:{rtt_port}")

        return True, proc.pid if keep_alive else None

    except FileNotFoundError:
        print("Error: JLinkGDBServer not found. Please install J-Link software.")
        return False, None
    except Exception as e:
        print(f"Error starting JLinkGDBServer: {e}")
        return False, None


def stop_gdb_server() -> bool:
    """
    Stop JLinkGDBServer using PID file.

    Returns:
        True if successfully stopped, False otherwise
    """
    if not GDB_SERVER_PID_FILE.exists():
        print("JLinkGDBServer is not running (no PID file)")
        return False

    try:
        pid = int(GDB_SERVER_PID_FILE.read_text().strip())
    except ValueError:
        print("Error: Invalid PID file")
        return False

    try:
        os.kill(pid, 0)  # Check if process exists
    except ProcessLookupError:
        print("JLinkGDBServer is not running (stale PID file)")
        GDB_SERVER_PID_FILE.unlink()
        return False

    print(f"Stopping JLinkGDBServer (PID: {pid})...")
    os.kill(pid, signal.SIGTERM)

    # Wait for graceful shutdown
    for _ in range(50):
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except ProcessLookupError:
            print("JLinkGDBServer stopped")
            if GDB_SERVER_PID_FILE.exists():
                GDB_SERVER_PID_FILE.unlink()
            return True

    # Force kill
    print("JLinkGDBServer did not stop gracefully, sending SIGKILL...")
    os.kill(pid, signal.SIGKILL)
    time.sleep(0.5)
    if GDB_SERVER_PID_FILE.exists():
        GDB_SERVER_PID_FILE.unlink()
    print("JLinkGDBServer stopped")
    return True


def gdb_server_status() -> tuple[bool, Optional[int]]:
    """
    Check JLinkGDBServer status.

    Returns:
        Tuple of (is_running, pid or None)
    """
    if not GDB_SERVER_PID_FILE.exists():
        return False, None

    try:
        pid = int(GDB_SERVER_PID_FILE.read_text().strip())
    except ValueError:
        GDB_SERVER_PID_FILE.unlink()
        return False, None

    try:
        os.kill(pid, 0)
        return True, pid
    except ProcessLookupError:
        GDB_SERVER_PID_FILE.unlink()
        return False, None


# ============================================================================
# CLI Command Handlers
# ============================================================================

def cmd_server(args: argparse.Namespace) -> int:
    """Handle 'server' subcommand - manage JLinkGDBServer."""
    if args.action == "start":
        if not args.device:
            print("Error: --device is required for starting JLinkGDBServer", file=sys.stderr)
            return 1

        # Check if already running
        running, pid = gdb_server_status()
        if running:
            print(f"JLinkGDBServer already running (PID: {pid})")
            return 0

        success, _ = start_gdb_server(
            device=args.device,
            speed=args.speed,
            interface=args.interface,
            gdb_port=args.gdb_port,
            rtt_port=args.rtt_port,
            keep_alive=True,
        )
        return 0 if success else 1

    elif args.action == "stop":
        success = stop_gdb_server()
        return 0 if success else 1

    elif args.action == "status":
        running, pid = gdb_server_status()
        if running:
            print(f"JLinkGDBServer is running (PID: {pid})")
            print(f"RTT available at {DEFAULT_RTT_HOST}:{DEFAULT_RTT_PORT}")
            return 0
        else:
            print("JLinkGDBServer is not running")
            return 1

    return 1


def cmd_daemon(args: argparse.Namespace) -> int:
    """Handle 'daemon' subcommand."""
    daemon = RTTDaemon(
        pid_file=args.pid_file,
        log_file=args.log_file,
        rtt_host=args.host,
        rtt_port=args.port,
        max_log_size=args.max_log_size,
        max_log_age=args.max_log_age,
    )

    if args.action == "start":
        try:
            daemon.start()
            print(f"RTT daemon started (PID: {daemon.pid})")
            print(f"Logging to: {daemon.config.log_file}")
            daemon.run()
        except DaemonAlreadyRunningError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\nInterrupted")
            daemon.cleanup()
            return 0

    elif args.action == "stop":
        pid_file = daemon.config.pid_file
        if not pid_file.exists():
            print("Daemon is not running (no PID file)")
            return 1

        try:
            pid = int(pid_file.read_text().strip())
        except ValueError:
            print("Error: Invalid PID file")
            return 1

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            print("Daemon is not running (stale PID file)")
            pid_file.unlink()
            return 1

        print(f"Stopping daemon (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)

        for _ in range(50):
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                print("Daemon stopped")
                if pid_file.exists():
                    pid_file.unlink()
                return 0

        print("Daemon did not stop gracefully, sending SIGKILL...")
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)
        if pid_file.exists():
            pid_file.unlink()
        print("Daemon stopped")
        return 0

    elif args.action == "status":
        pid_file = daemon.config.pid_file
        if not pid_file.exists():
            print("Daemon is not running")
            return 1

        try:
            pid = int(pid_file.read_text().strip())
        except ValueError:
            print("Error: Invalid PID file")
            return 1

        try:
            os.kill(pid, 0)
            print(f"Daemon is running (PID: {pid})")
            print(f"PID file: {pid_file}")
            print(f"Log file: {daemon.config.log_file}")
            return 0
        except ProcessLookupError:
            print("Daemon is not running (stale PID file)")
            pid_file.unlink()
            return 1

    return 1


def cmd_read(args: argparse.Namespace) -> int:
    """Handle 'read' subcommand."""
    log_dir = args.log_dir

    if args.since:
        lines = read_since(log_dir, args.since, pattern=args.pattern)
    elif args.grep:
        lines = grep_lines(
            log_dir,
            args.grep,
            case_sensitive=not args.ignore_case,
            regex=args.regex,
            log_pattern=args.pattern,
        )
    else:
        n = args.lines if args.lines else DEFAULT_LINES
        lines = read_lines(log_dir, n, pattern=args.pattern)

    # Strip ANSI by default unless --no-strip-ansi
    if not args.no_strip_ansi:
        lines = [strip_ansi(line) for line in lines]

    if not lines:
        print("(no matching lines)")
        return 0

    for line in lines:
        print(line)

    return 0


def send_command(
    command: str,
    host: str = DEFAULT_RTT_HOST,
    port: int = DEFAULT_RTT_PORT,
    wait_for_shell: bool = False,
    shell_timeout: float = DEFAULT_SHELL_TIMEOUT,
) -> str:
    """
    Send a command to RTT server. Does not read response.

    Args:
        command: Command to send
        host: RTT server hostname
        port: RTT server port
        wait_for_shell: Wait for shell prompt before sending
        shell_timeout: Timeout for shell prompt detection

    Returns:
        Empty string on success, error message on failure
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3.0)

        try:
            sock.connect((host, port))
        except ConnectionRefusedError:
            return "J-Link RTT server is not running on port 19021."
        except socket.timeout:
            return f"Connection to {host}:{port} timed out."

        # Wait for shell prompt if requested
        if wait_for_shell:
            sock.setblocking(0)
            start_time = time.time()
            shell_buffer = b""

            while (time.time() - start_time) < shell_timeout:
                try:
                    data = sock.recv(4096)
                    if data:
                        shell_buffer += data
                        if wait_for_shell_prompt(shell_buffer):
                            break
                except BlockingIOError:
                    time.sleep(0.05)
            sock.setblocking(1)

        # Send command
        sock.sendall((command + "\n").encode("utf-8"))
        sock.close()
        return ""

    except Exception as e:
        return f"Failed to send command: {e}"


def send_command_via_daemon(command: str, socket_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Send command to daemon via Unix Socket.

    Args:
        command: Command to send
        socket_path: Path to daemon command socket

    Returns:
        Tuple of (success, response_or_error)
    """
    if socket_path is None:
        socket_path = DEFAULT_PID_FILE_DIR.parent / ".rtt_tools" / "rtt_command.sock"

    if not socket_path.exists():
        return False, "Daemon command socket not found. Is daemon running?"

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(COMMAND_TIMEOUT + 2)
        sock.connect(str(socket_path))

        # Send command
        sock.sendall(command.encode("utf-8"))

        # Read response
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            # Check if we have a complete response
            if len(chunk) < 4096:
                break

        sock.close()
        return True, response.decode("utf-8", errors="replace")

    except socket.timeout:
        return False, "Command timed out"
    except ConnectionRefusedError:
        return False, "Cannot connect to daemon. Is it running?"
    except Exception as e:
        return False, f"Error: {e}"


def cmd_send(args: argparse.Namespace) -> int:
    """
    Handle 'send' subcommand.

    Sends a command via daemon Unix Socket, then reads response from daemon log file.
    Daemon must be running for this to work.
    """
    # Determine socket path
    socket_path = Path.home() / ".rtt_tools" / "rtt_command.sock"

    # Try to send via daemon
    success, response = send_command_via_daemon(args.command, socket_path)

    if success:
        # Strip ANSI by default
        if not args.no_strip_ansi:
            response = strip_ansi(response)
        print(response)
        return 0
    else:
        # Daemon not available, fall back to direct send (for compatibility)
        print(f"Warning: {response}", file=sys.stderr)
        print("Falling back to direct send (daemon may not be running)")

        error = send_command(
            command=args.command,
            host=args.host,
            port=args.port,
            wait_for_shell=args.wait_for_shell,
            shell_timeout=args.shell_timeout,
        )

        if error:
            print(error)
            return 1

        # Wait for device to process
        time.sleep(0.3)

        # Read response from daemon log file
        lines = read_lines(args.log_dir, args.lines, pattern=args.pattern)

        # Strip ANSI by default
        if not args.no_strip_ansi:
            lines = [strip_ansi(line) for line in lines]

        if lines:
            for line in lines:
                print(line)
        else:
            print("(no response captured)")

        return 0


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for unified CLI."""
    parser = argparse.ArgumentParser(
        description="J-Link RTT Tools - Unified CLI Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s server start -d nRF52840_XXAA    # Start JLinkGDBServer
  %(prog)s server status                    # Check server status
  %(prog)s server stop                      # Stop JLinkGDBServer
  %(prog)s daemon start                     # Start background daemon
  %(prog)s daemon stop                      # Stop daemon
  %(prog)s read --lines 50                  # Read latest 50 lines
  %(prog)s read --since 300                 # Read last 5 minutes
  %(prog)s read --grep "ERROR"              # Grep for ERROR
  %(prog)s send "help" -n 20                # Send command, read 20 lines from log

Log files are stored in ~/.rtt_tools/logs/ by default.
ANSI codes are stripped by default. Use --no-strip-ansi to keep them.
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Server subcommand (JLinkGDBServer management)
    server_parser = subparsers.add_parser(
        "server",
        help="Start/stop JLinkGDBServer (provides RTT on port 19021)"
    )
    server_parser.add_argument(
        "action",
        choices=["start", "stop", "status"],
        help="Server action"
    )
    server_parser.add_argument(
        "-d", "--device",
        type=str,
        default=None,
        help="Target device (required for start, e.g., nRF52840_XXAA)"
    )
    server_parser.add_argument(
        "--speed",
        type=int,
        default=DEFAULT_SPEED,
        help=f"J-Link speed in kHz (default: {DEFAULT_SPEED})"
    )
    server_parser.add_argument(
        "--interface",
        type=str,
        default=DEFAULT_INTERFACE,
        choices=["SWD", "JTAG"],
        help=f"Interface type (default: {DEFAULT_INTERFACE})"
    )
    server_parser.add_argument(
        "--gdb-port",
        type=int,
        default=DEFAULT_GDB_PORT,
        help=f"GDB server port (default: {DEFAULT_GDB_PORT})"
    )
    server_parser.add_argument(
        "--rtt-port",
        type=int,
        default=DEFAULT_RTT_PORT,
        help=f"RTT server port (default: {DEFAULT_RTT_PORT})"
    )
    server_parser.set_defaults(func=cmd_server)

    # Daemon subcommand
    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Manage background RTT log capture daemon"
    )
    daemon_parser.add_argument(
        "action",
        choices=["start", "stop", "status"],
        help="Daemon action"
    )
    daemon_parser.add_argument(
        "--pid-file",
        type=Path,
        default=None,
        help="Path to PID file"
    )
    daemon_parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to log file"
    )
    daemon_parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_RTT_HOST,
        help=f"RTT server hostname (default: {DEFAULT_RTT_HOST})"
    )
    daemon_parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_RTT_PORT,
        help=f"RTT server port (default: {DEFAULT_RTT_PORT})"
    )
    daemon_parser.add_argument(
        "--max-log-size",
        type=int,
        default=10 * 1024 * 1024,
        help="Max log file size in bytes before rotation"
    )
    daemon_parser.add_argument(
        "--max-log-age",
        type=int,
        default=24 * 60 * 60,
        help="Max log file age in seconds before rotation"
    )
    daemon_parser.set_defaults(func=cmd_daemon)

    # Read subcommand
    read_parser = subparsers.add_parser(
        "read",
        help="Read and query RTT log files"
    )
    read_parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help=f"Directory containing log files (default: {DEFAULT_LOG_DIR})"
    )
    read_parser.add_argument(
        "--pattern",
        type=str,
        default="rtt.log*",
        help="Glob pattern for log files (default: rtt.log*)"
    )
    read_parser.add_argument(
        "-n", "--lines",
        type=int,
        help=f"Number of lines to read (default: {DEFAULT_LINES})"
    )
    read_parser.add_argument(
        "--since",
        type=int,
        metavar="SECONDS",
        help="Read logs since N seconds ago"
    )
    read_parser.add_argument(
        "--grep",
        type=str,
        metavar="PAT",
        help="Grep for pattern"
    )
    read_parser.add_argument(
        "-i", "--ignore-case",
        action="store_true",
        help="Case-insensitive grep"
    )
    read_parser.add_argument(
        "-r", "--regex",
        action="store_true",
        help="Use regex matching"
    )
    read_parser.add_argument(
        "--no-strip-ansi",
        action="store_true",
        help="Keep ANSI escape sequences (default: stripped)"
    )
    read_parser.set_defaults(func=cmd_read)

    # Send subcommand
    send_parser = subparsers.add_parser(
        "send",
        help="Send command to device (response read from daemon log)"
    )
    send_parser.add_argument(
        "command",
        help="Command to send"
    )
    send_parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_RTT_HOST,
        help=f"RTT server hostname (default: {DEFAULT_RTT_HOST})"
    )
    send_parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_RTT_PORT,
        help=f"RTT server port (default: {DEFAULT_RTT_PORT})"
    )
    send_parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help=f"Directory containing log files (default: {DEFAULT_LOG_DIR})"
    )
    send_parser.add_argument(
        "--pattern",
        type=str,
        default="rtt.log*",
        help="Glob pattern for log files (default: rtt.log*)"
    )
    send_parser.add_argument(
        "-n", "--lines",
        type=int,
        default=20,
        help="Number of lines to read from log (default: 20)"
    )
    send_parser.add_argument(
        "--no-strip-ansi",
        action="store_true",
        help="Keep ANSI escape sequences (default: stripped)"
    )
    send_parser.add_argument(
        "--wait-for-shell",
        action="store_true",
        help="Wait for shell prompt before sending command"
    )
    send_parser.add_argument(
        "--shell-timeout",
        type=float,
        default=DEFAULT_SHELL_TIMEOUT,
        help=f"Timeout for shell prompt detection (default: {DEFAULT_SHELL_TIMEOUT}s)"
    )
    send_parser.set_defaults(func=cmd_send)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
