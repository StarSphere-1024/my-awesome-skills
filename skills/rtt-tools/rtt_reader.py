#!/usr/bin/env python3
"""
J-Link RTT Reader - A tool for interacting with Zephyr Shell over SEGGER J-Link RTT.

This script connects to the J-Link RTT telnet port, optionally sends a command,
and captures logs for a specified timeout period. Designed to prevent hanging
on the infinite RTT stream.

Features:
- Non-blocking read with timeout (prevents hanging)
- Optional ANSI color code stripping
- Graceful error handling for connection failures
- UTF-8 decoding with error recovery
- Shell prompt detection (--wait-for-shell) - waits for "rtt:~$" before sending commands
"""

import socket
import sys
import argparse
import time
import re
from typing import Optional, Tuple


# ANSI escape code pattern for stripping colors
ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Shell prompt pattern - matches Zephyr Shell prompt "rtt:~$ " or similar
SHELL_PROMPT_PATTERN = re.compile(rb"rtt:~\$|\[0m\[[0-9;]*mrtt:~\$|zephyr.*>|\(zephyr\).*#")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences (colors, cursor control) from text."""
    return ANSI_ESCAPE_PATTERN.sub("", text)


def wait_for_shell_prompt(
    data: bytes,
    timeout: float = 10.0
) -> Tuple[bool, str]:
    """
    Check if shell prompt is detected in data stream.

    Args:
        data: Raw bytes received from RTT stream
        timeout: Not used in this synchronous version - kept for API compatibility

    Returns:
        Tuple of (prompt_detected, decoded_output)
    """
    text = data.decode("utf-8", errors="replace")
    prompt_detected = bool(SHELL_PROMPT_PATTERN.search(data))
    return prompt_detected, text


def read_rtt(
    timeout: int = 3,
    command: str = None,
    host: str = "127.0.0.1",
    port: int = 19021,
    strip_ansi_codes: bool = True,
    wait_for_shell: bool = False,
    shell_timeout: float = 10.0,
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
        sock.setblocking(1)  # Use socket timeout for controlled blocking

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
                        detected, _ = wait_for_shell_prompt(shell_buffer)
                        if detected:
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
                # Timeout waiting for shell - send command anyway but warn
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
                    # Decode with error handling for dropped bytes
                    text = data.decode("utf-8", errors="replace")
                    if strip_ansi_codes:
                        text = strip_ansi(text)
                    output_lines.append(text)
            except BlockingIOError:
                # No data available, continue waiting
                time.sleep(0.05)
            except socket.timeout:
                break

        sock.close()

        return "".join(output_lines)

    except Exception as e:
        return f"Unexpected error reading RTT: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Read Zephyr Shell logs over J-Link RTT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Read logs for 3 seconds
  %(prog)s -t 5                     # Read logs for 5 seconds
  %(prog)s -c "help"                # Send 'help' command, read response
  %(prog)s -c "sys reboot" -t 2     # Reboot device, capture 2s of output
  %(prog)s --host 192.168.1.100     # Connect to remote J-Link server
  %(prog)s --strip-ansi             # Strip ANSI color codes from output
  %(prog)s -c "log level 3" --strip-ansi  # Set log level, clean output
  %(prog)s -c "help" --wait-for-shell -t 5  # Wait for shell, then send command
        """,
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=3,
        help="Seconds to listen for RTT output (default: 3)",
    )
    parser.add_argument(
        "-c",
        "--command",
        type=str,
        default=None,
        help="Zephyr Shell command to send before reading logs",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="RTT server hostname (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=19021, help="RTT server port (default: 19021)"
    )
    parser.add_argument(
        "--no-strip-ansi",
        action="store_false",
        dest="strip_ansi",
        default=True,
        help="Keep ANSI escape sequences (colors) from output (default: stripped)",
    )
    parser.add_argument(
        "--wait-for-shell",
        action="store_true",
        help="Wait for shell prompt (rtt:~$) before sending command",
    )
    parser.add_argument(
        "--shell-timeout",
        type=float,
        default=10.0,
        help="Timeout for waiting for shell prompt in seconds (default: 10)",
    )

    args = parser.parse_args()
    result = read_rtt(
        timeout=args.timeout,
        command=args.command,
        host=args.host,
        port=args.port,
        strip_ansi_codes=args.strip_ansi,
        wait_for_shell=args.wait_for_shell,
        shell_timeout=args.shell_timeout,
    )
    print(result)

    # Exit with error code if connection failed
    if "not running" in result.lower() or "failed" in result.lower():
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
