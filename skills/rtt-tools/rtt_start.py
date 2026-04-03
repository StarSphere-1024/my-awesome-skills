#!/usr/bin/env python3
"""
J-Link RTT One-Key Starter - Complete workflow to start RTT debugging.

This script automates the full RTT setup workflow:
1. Kill any existing J-Link processes
2. Start JLinkGDBServer in background
3. Optionally flash and reset the target
4. Connect RTT client and display logs

--device is REQUIRED. All other settings have safe defaults.

New features:
- --keep-alive: Run JLinkGDBServer in background, create PID file
- --pid-file-dir: Custom directory for PID file (default: ~/.rtt_tools)
"""

import subprocess
import sys
import argparse
import time
import os
import signal
import atexit
from pathlib import Path
from typing import Optional


# Safe defaults that don't vary by project (ports, timing)
# Project-specific settings (device, elf_file) MUST be provided via CLI
DEFAULT_CONFIG = {
    "speed": 4000,
    "interface": "SWD",
    "rtt_port": 19021,
    "gdb_port": 2331,
    "reset": True,
    "strip_ansi": True,
    "timeout": 3,
}

# Default PID file directory
DEFAULT_PID_FILE_DIR = Path.home() / ".rtt_tools"


def write_pid_file(pid: int, pid_file: Path) -> None:
    """Write PID to file for later retrieval by rtt_stop.py."""
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid))


def read_pid_file(pid_file: Path) -> Optional[int]:
    """Read PID from file. Returns None if file doesn't exist or is invalid."""
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text().strip())
    except ValueError:
        return None


def remove_pid_file(pid_file: Path) -> None:
    """Remove PID file."""
    if pid_file.exists():
        pid_file.unlink()


class RTTStarter:
    def __init__(self, config: dict):
        self.config = config
        self.gdb_server_proc = None

    def cleanup_on_exit(self):
        """Clean up background processes on exit."""
        if self.gdb_server_proc and self.gdb_server_proc.poll() is None:
            print("\nStopping JLinkGDBServer...")
            self.gdb_server_proc.terminate()
            try:
                self.gdb_server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.gdb_server_proc.kill()

    def find_jlink_processes(self):
        """Find all J-Link related processes."""
        processes = []
        try:
            result = subprocess.run(
                ["pgrep", "-af", "JLink"], capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split(maxsplit=1)
                        if len(parts) >= 2:
                            processes.append({"pid": int(parts[0]), "cmd": parts[1]})
        except FileNotFoundError:
            pass
        return processes

    def kill_jlink_processes(self):
        """Kill existing J-Link processes."""
        processes = self.find_jlink_processes()
        if not processes:
            return

        print(f"Cleaning up {len(processes)} existing J-Link process(es)...")
        for proc in processes:
            try:
                os.kill(proc["pid"], signal.SIGTERM)
            except ProcessLookupError:
                pass
        time.sleep(0.5)

    def start_gdb_server(self, keep_alive: bool = False, pid_file_dir: Optional[Path] = None):
        """Start JLinkGDBServer in background.

        Args:
            keep_alive: If True, run in background and create PID file
            pid_file_dir: Directory for PID file (default: ~/.rtt_tools)
        """
        device = self.config["device"]
        speed = self.config["speed"]
        iface = self.config["interface"]
        gdb_port = self.config["gdb_port"]
        rtt_port = self.config["rtt_port"]

        cmd = [
            "JLinkGDBServer",
            "-device",
            device,
            "-if",
            iface,
            "-speed",
            str(speed),
            "-port",
            str(gdb_port),
            "-rttport",
            str(rtt_port),
            "-single",
        ]

        print(
            f"Starting JLinkGDBServer (device={device}, if={iface}, speed={speed})..."
        )

        self.gdb_server_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

        print("Waiting for GDB server to initialize...")
        time.sleep(2)

        if self.gdb_server_proc.poll() is not None:
            print("Error: JLinkGDBServer failed to start.")
            return False

        if keep_alive:
            # Write PID file and exit - server runs in background
            if pid_file_dir is None:
                pid_file_dir = DEFAULT_PID_FILE_DIR
            pid_file = pid_file_dir / "gdb_server.pid"
            write_pid_file(self.gdb_server_proc.pid, pid_file)

            print(f"JLinkGDBServer started in background (PID: {self.gdb_server_proc.pid})")
            print(f"PID file: {pid_file}")
            print(f"Run 'rtt_stop.py' to stop the server.")
            return True

        print("JLinkGDBServer started successfully.")
        return True

    def flash_target(self):
        """Flash the target device if ELF file is specified."""
        elf_file = self.config.get("elf_file")
        if not elf_file:
            print("No ELF file specified, skipping flash.")
            return True

        if not os.path.exists(elf_file):
            print(f"Error: ELF file not found: {elf_file}")
            return False

        device = self.config["device"]
        speed = self.config["speed"]
        iface = self.config["interface"]

        print(f"Flashing {elf_file}...")

        # Use JLinkExe for flashing (more universally available)
        hex_file = elf_file.replace(".elf", ".hex")
        if not os.path.exists(hex_file):
            hex_file = elf_file  # Fallback to ELF if HEX not found

        flash_script = f"""
device {device}
speed {speed}
if {iface}
loadfile {hex_file}
r
g
q
"""
        try:
            result = subprocess.run(
                ["JLinkExe"],
                input=flash_script,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                print(f"Flash failed: {result.stderr}")
                return False
            print("Flash completed.")
            return True
        except subprocess.TimeoutExpired:
            print("Flash timed out.")
            return False
        except FileNotFoundError:
            print("JLinkExe not found.")
            return False

    def reset_target(self):
        """Reset the target device."""
        if not self.config.get("reset", True):
            return

        print("Resetting target...")
        device = self.config["device"]
        speed = self.config["speed"]
        iface = self.config["interface"]

        reset_script = f"""
device {device}
speed {speed}
if {iface}
r
g
q
"""
        try:
            result = subprocess.run(
                ["JLinkExe"],
                input=reset_script,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                print("Target reset.")
            else:
                print(f"Reset warning: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("Reset timed out, continuing anyway...")
        except FileNotFoundError:
            print("JLinkExe not found, skipping hardware reset.")

    def read_rtt(self):
        """Read RTT logs using rtt_reader.py."""
        from pathlib import Path

        script_dir = Path(__file__).parent
        rtt_reader = script_dir / "rtt_reader.py"

        if not rtt_reader.exists():
            print("Error: rtt_reader.py not found.")
            return

        cmd = [
            sys.executable,
            str(rtt_reader),
            "-t",
            str(self.config["timeout"]),
        ]

        if not self.config.get("strip_ansi", True):
            cmd.append("--no-strip-ansi")

        print(f"\nReading RTT output (timeout={self.config['timeout']}s)...")
        print("-" * 60)

        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        print("-" * 60)

    def run(self, keep_alive: bool = False, pid_file_dir: Optional[Path] = None):
        """Run the complete RTT startup workflow.

        Args:
            keep_alive: If True, start JLinkGDBServer in background and exit
            pid_file_dir: Directory for PID file
        """
        print("=" * 60)
        print("J-Link RTT One-Key Starter")
        print("=" * 60)

        # Only register cleanup if not in keep-alive mode
        if not keep_alive:
            atexit.register(self.cleanup_on_exit)

        self.kill_jlink_processes()

        if not self.start_gdb_server(keep_alive=keep_alive, pid_file_dir=pid_file_dir):
            return 1

        # If keep-alive mode, exit after starting server
        if keep_alive:
            return 0

        if self.config.get("flash", False):
            if not self.flash_target():
                return 1

        self.reset_target()
        self.read_rtt()

        print("\nRTT session ready. The GDB server is running in background.")
        print("Run 'rtt_reader.py -t 3' to read more logs.")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="One-key J-Link RTT starter - automates full debugging workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -d nRF52840_XXAA                # Minimal: just device
  %(prog)s -d nRF52840_XXAA --keep-alive   # Start GDB server in background
  %(prog)s -d nRF52832_XXAA --flash --elf build/zephyr/zephyr.elf
  %(prog)s -d nRF52840_XXAA --no-reset
  %(prog)s -d nRF52840_XXAA --timeout 5

Note: --device is REQUIRED. --elf is required when using --flash.
        """,
    )

    # Required arguments
    parser.add_argument(
        "--device",
        "-d",
        required=True,
        help="Target device (e.g., nRF52840_XXAA, nRF52832_XXAA) - REQUIRED",
    )

    # Optional arguments with safe defaults
    parser.add_argument(
        "--speed", type=int, default=4000, help="J-Link speed in kHz (default: 4000)"
    )
    parser.add_argument(
        "--interface",
        "-i",
        default="SWD",
        choices=["SWD", "JTAG"],
        help="Interface (default: SWD)",
    )
    parser.add_argument(
        "--elf", default=None, help="ELF file to flash (required with --flash)"
    )
    parser.add_argument(
        "--flash", action="store_true", help="Flash the target before reading RTT"
    )
    parser.add_argument("--no-reset", action="store_true", help="Skip target reset")
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=3,
        help="RTT read timeout in seconds (default: 3)",
    )
    parser.add_argument(
        "--no-strip-ansi", action="store_true", help="Don't strip ANSI color codes"
    )
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="Start JLinkGDBServer in background and exit (creates PID file)",
    )
    parser.add_argument(
        "--pid-file-dir",
        type=Path,
        default=None,
        help=f"Directory for PID file (default: {DEFAULT_PID_FILE_DIR})",
    )

    args = parser.parse_args()

    # Validate flash requires elf
    if args.flash and not args.elf:
        print("Error: --elf is required when using --flash")
        sys.exit(1)

    # Build config
    config = {
        **DEFAULT_CONFIG,
        "device": args.device,
        "speed": args.speed,
        "interface": args.interface,
        "elf_file": args.elf,
        "flash": args.flash,
        "reset": not args.no_reset,
        "strip_ansi": not args.no_strip_ansi,
        "timeout": args.timeout,
    }

    starter = RTTStarter(config)
    sys.exit(starter.run(keep_alive=args.keep_alive, pid_file_dir=args.pid_file_dir))


if __name__ == "__main__":
    main()
