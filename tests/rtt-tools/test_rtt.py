#!/usr/bin/env python3

import socket
import subprocess
import sys
import threading
from io import StringIO
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "rtt-tools" / "scripts"))

from rtt import (
    build_jlink_gdb_server_cmd,
    capture_reconnecting,
    capture_rtt,
    drain_rtt,
    find_gdb,
    reset_and_go_via_gdb,
    send_command_and_read,
    start_server,
    strip_ansi,
    wait_for_rtt_socket,
)


def test_build_jlink_gdb_server_cmd_matches_jlink_rtt_shape():
    cmd = build_jlink_gdb_server_cmd(
        device="NRF54L15_M33",
        interface="SWD",
        speed="4000",
        gdb_port=2331,
        rtt_port=19021,
    )

    assert cmd[:3] == ["JLinkGDBServer", "-select", "usb"]
    assert ["-device", "NRF54L15_M33"] == cmd[cmd.index("-device"):cmd.index("-device") + 2]
    assert ["-rtttelnetport", "19021"] == cmd[cmd.index("-rtttelnetport"):cmd.index("-rtttelnetport") + 2]
    assert "-nohalt" in cmd
    assert "-singlerun" in cmd
    assert "-nogui" in cmd


def test_build_jlink_gdb_server_cmd_uses_dev_id():
    cmd = build_jlink_gdb_server_cmd(device="NRF54L15_M33", dev_id="608888244")

    assert cmd[cmd.index("-select") + 1] == "usb=608888244"


def test_strip_ansi_removes_rtt_prompt_codes():
    text = "\x1b[1;32mrtt:~$ \x1b[mkernel uptime\r\n"

    assert strip_ansi(text) == "rtt:~$ kernel uptime\r\n"


def test_wait_for_rtt_socket_connects_to_listening_port():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    accepted = []

    def accept_once():
        conn, _ = server.accept()
        accepted.append(conn)

    thread = threading.Thread(target=accept_once)
    thread.start()

    client = wait_for_rtt_socket("127.0.0.1", port, timeout=1.0)
    client.close()
    thread.join(timeout=1.0)
    server.close()
    for conn in accepted:
        conn.close()

    assert accepted


def test_send_command_and_read_writes_command_and_reads_response():
    left, right = socket.socketpair()

    def target():
        data = right.recv(4096)
        assert data == b"kernel uptime\n"
        right.sendall(b"\x1b[1;32mrtt:~$ \x1b[mkernel uptime\r\nUptime: 42 ms\r\n")
        right.close()

    thread = threading.Thread(target=target)
    thread.start()
    response = send_command_and_read(left, "kernel uptime", timeout=1.0)
    left.close()
    thread.join(timeout=1.0)

    assert "kernel uptime" in response
    assert "Uptime: 42 ms" in response
    assert "\x1b[" not in response


def test_capture_rtt_reads_available_output():
    left, right = socket.socketpair()
    right.sendall(b"\x1b[1;32mrtt:~$ \x1b[mboot line\r\n")
    right.close()

    output = StringIO()
    capture_rtt(left, seconds=1.0, output_stream=output)
    left.close()

    assert output.getvalue() == "rtt:~$ boot line\r\n"


def test_drain_rtt_discards_stale_output():
    left, right = socket.socketpair()
    right.sendall(b"old boot log\r\n")

    drain_rtt(left, quiet=0.01, timeout=0.2)
    right.sendall(b"new boot log\r\n")

    output = StringIO()
    capture_rtt(left, seconds=0.2, output_stream=output)
    left.close()
    right.close()

    assert output.getvalue() == "new boot log\r\n"


def test_start_server_suppresses_jlink_output_by_default(monkeypatch):
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            calls.append((cmd, kwargs))

    monkeypatch.setattr("rtt.subprocess.Popen", FakePopen)

    start_server(
        SimpleNamespace(
            device="NRF54L15_M33",
            dev_id=None,
            interface="SWD",
            speed="4000",
            gdb_port=2331,
            rtt_port=19021,
            endian="little",
            gdbserver="JLinkGDBServer",
            halt=False,
            no_single_run=False,
            tool_opt=[],
            verbose=False,
        )
    )

    _, kwargs = calls[0]
    assert kwargs["stdout"] == subprocess.DEVNULL
    assert kwargs["stderr"] == subprocess.DEVNULL


def test_capture_reconnecting_reads_after_socket_drop():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(2)
    port = server.getsockname()[1]

    def serve():
        first, _ = server.accept()
        first.sendall(b"SEGGER banner\r\n")
        first.close()
        second, _ = server.accept()
        second.sendall(b"boot line\r\n")
        second.close()
        server.close()

    thread = threading.Thread(target=serve)
    thread.start()

    output = StringIO()
    capture_reconnecting(
        host="127.0.0.1",
        port=port,
        seconds=1.0,
        connect_timeout=1.0,
        output_stream=output,
    )
    thread.join(timeout=1.0)

    assert "SEGGER banner" in output.getvalue()
    assert "boot line" in output.getvalue()


def test_find_gdb_prefers_explicit_path():
    assert find_gdb("/tmp/custom-gdb") == "/tmp/custom-gdb"


def test_reset_and_go_via_gdb_builds_monitor_command(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("rtt.subprocess.run", fake_run)

    reset_and_go_via_gdb(
        host="127.0.0.1",
        port=2331,
        gdb="/tmp/gdb",
        elf_file="/tmp/app.elf",
    )

    cmd, kwargs = calls[0]
    assert cmd[:4] == ["/tmp/gdb", "-q", "-nx", "-batch"]
    assert "/tmp/app.elf" in cmd
    assert "target extended-remote 127.0.0.1:2331" in cmd
    assert "monitor reset" in cmd
    assert "monitor go" in cmd
    assert kwargs["check"] is True
