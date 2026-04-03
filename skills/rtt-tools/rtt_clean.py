#!/usr/bin/env python3
"""
J-Link Cleaner - Kill occupied J-Link processes to release the RTT port.

This script finds and terminates J-Link related processes that may be
holding onto the RTT telnet port (19021), allowing you to start fresh.
"""

import subprocess
import sys
import argparse


def find_jlink_processes():
    """Find all J-Link related processes."""
    jlink_keywords = ["JLinkExe", "JLinkGDBServer", "JLinkRTTClient", "J-Link"]
    processes = []

    try:
        # Use pgrep to find J-Link processes
        result = subprocess.run(
            ["pgrep", "-af", "JLink"], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(maxsplit=1)
                    if len(parts) >= 2:
                        pid = int(parts[0])
                        cmd = parts[1]
                        processes.append({"pid": pid, "cmd": cmd})
    except FileNotFoundError:
        # pgrep not available, try ps + grep approach
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if "JLink" in line and "grep" not in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            pid = int(parts[1])
                            cmd = " ".join(parts[10:])
                            processes.append({"pid": pid, "cmd": cmd})
        except Exception as e:
            print(f"Error finding processes: {e}")

    return processes


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill a process by PID.

    Args:
        pid: Process ID to kill
        force: If True, use SIGKILL instead of SIGTERM

    Returns:
        True if successfully killed, False otherwise
    """
    try:
        signal = 9 if force else 15
        subprocess.run(["kill", f"-{signal}", str(pid)], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Failed to kill PID {pid}: {e}")
        return False
    except Exception as e:
        print(f"  Error killing PID {pid}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Kill J-Link processes that may be occupying the RTT port",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # List and kill all J-Link processes
  %(prog)s --list       # Only list processes, don't kill
  %(prog)s --force      # Use SIGKILL instead of SIGTERM
  %(prog)s --pid 12345  # Kill specific PID only
        """,
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Only list J-Link processes, don't kill them",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Use SIGKILL (kill -9) instead of SIGTERM",
    )
    parser.add_argument(
        "--pid", "-p", type=int, default=None, help="Kill specific PID only"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    # Handle specific PID kill
    if args.pid:
        print(f"Killing PID {args.pid}...")
        if kill_process(args.pid, args.force):
            print("Done.")
            sys.exit(0)
        else:
            sys.exit(1)

    # Find all J-Link processes
    print("Searching for J-Link processes...")
    processes = find_jlink_processes()

    if not processes:
        print("No J-Link processes found.")
        sys.exit(0)

    print(f"\nFound {len(processes)} J-Link process(s):")
    print("-" * 60)
    for proc in processes:
        print(f"  PID {proc['pid']}: {proc['cmd'][:50]}...")
    print("-" * 60)

    if args.list:
        print(
            "\nUse --force to kill these processes or --pid <PID> to kill specific one."
        )
        sys.exit(0)

    # Confirm before killing
    if not args.yes:
        confirm = input(f"\nKill all {len(processes)} process(es)? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Kill all processes
    print("\nKilling processes...")
    killed = 0
    failed = 0
    for proc in processes:
        if kill_process(proc["pid"], args.force):
            killed += 1
        else:
            failed += 1

    print(f"\nDone: {killed} killed, {failed} failed.")
    if failed > 0:
        print("Tip: Try --force flag for stubborn processes.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
