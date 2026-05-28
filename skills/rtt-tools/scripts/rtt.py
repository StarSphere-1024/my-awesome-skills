#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
West-style J-Link RTT console for Zephyr targets.

This keeps the useful part of Zephyr's `west rtt` flow inside the skill:
start JLinkGDBServer with an RTT telnet port, keep the target running with
`-nohalt`, connect one TCP socket, then bridge stdin/stdout or run one command.
"""

from __future__ import annotations

import argparse
import os
import re
import selectors
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_GDB_PORT = 2331
DEFAULT_RTT_PORT = 19021
DEFAULT_SPEED = "4000"
DEFAULT_INTERFACE = "SWD"
DEFAULT_ENDIAN = "little"
DEFAULT_GDBSERVER = "JLinkGDBServer"
DEFAULT_DEVICE = "NRF54L15_M33"
SOCKET_CHUNK_SIZE = 4096

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def build_jlink_gdb_server_cmd(
    *,
    device: str,
    dev_id: str | None = None,
    interface: str = DEFAULT_INTERFACE,
    speed: str = DEFAULT_SPEED,
    gdb_port: int = DEFAULT_GDB_PORT,
    rtt_port: int = DEFAULT_RTT_PORT,
    endian: str = DEFAULT_ENDIAN,
    gdbserver: str = DEFAULT_GDBSERVER,
    nohalt: bool = True,
    silent: bool = True,
    single_run: bool = True,
    nogui: bool = True,
    tool_opt: Sequence[str] | None = None,
) -> list[str]:
    """Build the JLinkGDBServer command used by Zephyr's jlink RTT runner."""
    select = f"usb={dev_id}" if dev_id else "usb"
    cmd = [
        gdbserver,
        "-select",
        select,
        "-port",
        str(gdb_port),
        "-if",
        interface,
        "-speed",
        str(speed),
        "-device",
        device,
    ]
    if silent:
        cmd.append("-silent")
    cmd += ["-endian", endian]
    if single_run:
        cmd.append("-singlerun")
    if nogui:
        cmd.append("-nogui")
    cmd += ["-rtttelnetport", str(rtt_port)]
    if nohalt:
        cmd.append("-nohalt")
    if tool_opt:
        cmd += list(tool_opt)
    return cmd


def wait_for_rtt_socket(
    host: str,
    port: int,
    *,
    timeout: float = 10.0,
    server_proc: subprocess.Popen | None = None,
) -> socket.socket:
    """Wait until the RTT telnet port accepts a connection."""
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None

    while time.monotonic() < deadline:
        if server_proc is not None and server_proc.poll() is not None:
            raise RuntimeError(f"JLinkGDBServer exited with code {server_proc.returncode}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            return sock
        except OSError as exc:
            last_error = exc
            sock.close()
            time.sleep(0.1)

    raise TimeoutError(f"Timed out waiting for RTT at {host}:{port}: {last_error}")


def stream_console(
    sock: socket.socket,
    *,
    input_stream=sys.stdin,
    output_stream=sys.stdout,
) -> None:
    """Bridge stdin/stdout to a connected RTT socket, like west's telnet loop."""
    sel = selectors.DefaultSelector()
    sel.register(input_stream, selectors.EVENT_READ)
    sel.register(sock, selectors.EVENT_READ)

    try:
        while True:
            for key, _ in sel.select():
                if key.fileobj == input_stream:
                    text = input_stream.readline()
                    if not text:
                        return
                    sock.sendall(text.encode("utf-8"))
                elif key.fileobj == sock:
                    data = sock.recv(SOCKET_CHUNK_SIZE)
                    if not data:
                        return
                    output_stream.write(data.decode("utf-8", errors="replace"))
                    output_stream.flush()
    finally:
        sel.close()


def send_command_and_read(
    sock: socket.socket,
    command: str,
    *,
    timeout: float = 5.0,
    strip: bool = True,
) -> str:
    """Send one Zephyr shell command and return RTT output collected by timeout."""
    sock.setblocking(False)

    # Drain stale banner/log bytes so the response is easier to inspect.
    drain_deadline = time.monotonic() + 0.25
    while time.monotonic() < drain_deadline:
        try:
            sock.recv(SOCKET_CHUNK_SIZE)
        except BlockingIOError:
            time.sleep(0.02)

    sock.sendall((command + "\n").encode("utf-8"))

    chunks: list[bytes] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            data = sock.recv(SOCKET_CHUNK_SIZE)
        except BlockingIOError:
            time.sleep(0.05)
            continue
        if not data:
            break
        chunks.append(data)

    text = b"".join(chunks).decode("utf-8", errors="replace")
    return strip_ansi(text) if strip else text


def find_gdb(explicit: str | None = None) -> str:
    """Find a GDB executable suitable for issuing J-Link monitor commands."""
    if explicit:
        return explicit

    sdk_dir = os.environ.get("ZEPHYR_SDK_INSTALL_DIR")
    if sdk_dir:
        candidate = Path(sdk_dir) / "arm-zephyr-eabi" / "bin" / "arm-zephyr-eabi-gdb"
        if candidate.exists():
            return str(candidate)

    for name in ("arm-zephyr-eabi-gdb", "gdb-multiarch", "gdb"):
        path = shutil.which(name)
        if path:
            return path

    raise RuntimeError("GDB not found; pass --gdb or source the Zephyr/NCS environment")


def reset_and_go_via_gdb(
    *,
    host: str,
    port: int,
    gdb: str | None = None,
    elf_file: str | None = None,
) -> None:
    """Ask JLinkGDBServer to reset and run the target."""
    cmd = [find_gdb(gdb), "-q", "-nx", "-batch"]
    if elf_file:
        cmd.append(elf_file)
    cmd += [
        "-ex",
        f"target extended-remote {host}:{port}",
        "-ex",
        "monitor reset",
        "-ex",
        "monitor go",
        "-ex",
        "detach",
        "-ex",
        "quit",
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def capture_rtt(
    sock: socket.socket,
    *,
    seconds: float,
    strip: bool = True,
    output_stream=sys.stdout,
) -> None:
    """Print RTT output for a bounded duration."""
    sock.setblocking(False)
    deadline = time.monotonic() + seconds

    while time.monotonic() < deadline:
        try:
            data = sock.recv(SOCKET_CHUNK_SIZE)
        except BlockingIOError:
            time.sleep(0.02)
            continue
        if not data:
            return

        text = data.decode("utf-8", errors="replace")
        if strip:
            text = strip_ansi(text)
        output_stream.write(text)
        output_stream.flush()


def capture_reconnecting(
    *,
    host: str,
    port: int,
    seconds: float,
    connect_timeout: float,
    strip: bool = True,
    output_stream=sys.stdout,
) -> None:
    """Capture RTT output, reconnecting when J-Link drops the telnet socket."""
    deadline = time.monotonic() + seconds

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        try:
            sock = wait_for_rtt_socket(
                host,
                port,
                timeout=min(connect_timeout, max(0.1, remaining)),
            )
        except TimeoutError:
            return

        try:
            capture_rtt(
                sock,
                seconds=max(0.0, deadline - time.monotonic()),
                strip=strip,
                output_stream=output_stream,
            )
        finally:
            sock.close()

        time.sleep(0.05)


def drain_rtt(sock: socket.socket, *, quiet: float = 0.2, timeout: float = 2.0) -> None:
    """Discard stale RTT bytes until the stream is quiet or timeout expires."""
    sock.setblocking(False)
    deadline = time.monotonic() + timeout
    quiet_deadline = time.monotonic() + quiet

    while time.monotonic() < deadline:
        try:
            data = sock.recv(SOCKET_CHUNK_SIZE)
        except BlockingIOError:
            if time.monotonic() >= quiet_deadline:
                return
            time.sleep(0.02)
            continue
        if not data:
            return
        quiet_deadline = time.monotonic() + quiet


def start_server(args: argparse.Namespace) -> subprocess.Popen:
    cmd = build_jlink_gdb_server_cmd(
        device=args.device,
        dev_id=args.dev_id,
        interface=args.interface,
        speed=args.speed,
        gdb_port=args.gdb_port,
        rtt_port=args.rtt_port,
        endian=args.endian,
        gdbserver=args.gdbserver,
        nohalt=not args.halt,
        single_run=not getattr(args, "no_single_run", False),
        tool_opt=args.tool_opt,
    )
    if args.verbose:
        print("Starting:", " ".join(cmd), file=sys.stderr)
    return subprocess.Popen(
        cmd,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        stdout=None if args.verbose else subprocess.DEVNULL,
        stderr=None if args.verbose else subprocess.DEVNULL,
    )


def run_with_socket(args: argparse.Namespace, fn) -> int:
    proc = None
    sock = None
    try:
        if not args.attach:
            proc = start_server(args)
        sock = wait_for_rtt_socket(
            args.host,
            args.rtt_port,
            timeout=args.connect_timeout,
            server_proc=proc,
        )
        fn(sock)
        return 0
    finally:
        if sock is not None:
            sock.close()
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def cmd_console(args: argparse.Namespace) -> int:
    if not sys.stdin.isatty():
        print("error: console mode needs a TTY; use `command` for automation", file=sys.stderr)
        return 2
    return run_with_socket(args, lambda sock: stream_console(sock))


def cmd_command(args: argparse.Namespace) -> int:
    def _run(sock: socket.socket) -> None:
        response = send_command_and_read(
            sock,
            args.command,
            timeout=args.timeout,
            strip=not args.no_strip_ansi,
        )
        print(response, end="" if response.endswith("\n") else "\n")

    return run_with_socket(args, _run)


def cmd_capture(args: argparse.Namespace) -> int:
    def _run(sock: socket.socket) -> None:
        if not args.reset:
            capture_rtt(sock, seconds=args.seconds, strip=not args.no_strip_ansi)
            return

        if not args.no_drain:
            drain_rtt(sock, quiet=args.drain_quiet, timeout=args.drain_timeout)

        try:
            time.sleep(args.reset_delay)
            reset_and_go_via_gdb(
                host=args.host,
                port=args.gdb_port,
                gdb=args.gdb,
                elf_file=args.elf_file,
            )
            sock.close()
            time.sleep(args.post_reset_delay)
            capture_reconnecting(
                host=args.host,
                port=args.rtt_port,
                seconds=args.seconds,
                connect_timeout=args.connect_timeout,
                strip=not args.no_strip_ansi,
            )
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip() if exc.stderr else str(exc)
            raise RuntimeError(f"GDB reset failed: {message}") from exc


    return run_with_socket(args, _run)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-d", "--device", default=DEFAULT_DEVICE)
    parser.add_argument("--dev-id")
    parser.add_argument("--interface", default=DEFAULT_INTERFACE)
    parser.add_argument("--speed", default=DEFAULT_SPEED)
    parser.add_argument("--gdb-port", type=int, default=DEFAULT_GDB_PORT)
    parser.add_argument("--rtt-port", type=int, default=DEFAULT_RTT_PORT)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--endian", choices=["little", "big"], default=DEFAULT_ENDIAN)
    parser.add_argument("--gdbserver", default=DEFAULT_GDBSERVER)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--attach", action="store_true", help="connect to an existing RTT server")
    parser.add_argument("--halt", action="store_true", help="omit JLinkGDBServer -nohalt")
    parser.add_argument("--verbose", action="store_true", help="show JLinkGDBServer startup output")
    parser.add_argument(
        "-O",
        "--tool-opt",
        action="append",
        default=[],
        help="extra option passed to JLinkGDBServer; repeat as needed",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="J-Link RTT console for Zephyr targets")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    console = sub.add_parser("console", help="interactive RTT console")
    add_common_args(console)
    console.set_defaults(func=cmd_console)

    command = sub.add_parser("command", help="send one Zephyr shell command")
    add_common_args(command)
    command.add_argument("command")
    command.add_argument("--timeout", type=float, default=5.0)
    command.add_argument("--no-strip-ansi", action="store_true")
    command.set_defaults(func=cmd_command)

    capture = sub.add_parser("capture", help="capture RTT output, optionally after target reset")
    add_common_args(capture)
    capture.add_argument("--seconds", type=float, default=10.0)
    capture.add_argument("--reset", action="store_true", help="reset and run target after RTT reader is active")
    capture.add_argument("--reset-delay", type=float, default=0.1, help="delay between reader start and reset")
    capture.add_argument("--post-reset-delay", type=float, default=0.2, help="delay before reconnecting RTT after reset")
    capture.add_argument("--no-drain", action="store_true", help="keep stale RTT bytes before --reset")
    capture.add_argument("--drain-quiet", type=float, default=0.2, help="quiet time before stale drain ends")
    capture.add_argument("--drain-timeout", type=float, default=2.0, help="maximum stale drain duration")
    capture.add_argument("--gdb", help="GDB executable for --reset")
    capture.add_argument("--elf-file", help="optional ELF file passed to GDB")
    capture.add_argument("--no-strip-ansi", action="store_true")
    capture.set_defaults(func=cmd_capture, no_single_run=True)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
