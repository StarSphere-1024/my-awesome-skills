#!/usr/bin/env python3
"""Git commit tool with atomic analysis and Conventional Commit generation."""

import subprocess
import sys
import os

# Add scripts directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from check_staged_changes import check_staged_changes
from analyze_atomicity import analyze_atomicity
from generate_commit_message import (
    get_staged_diff,
    COMMIT_MESSAGE_PROMPT,
    validate_subject,
    generate_with_llm,
    get_manual_commit_message
)


def run_command(cmd):
    """Run shell command and return output.

    Args:
        cmd: Command string or list

    Returns:
        tuple: (returncode, stdout, stderr)
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=isinstance(cmd, str)
    )
    return result.returncode, result.stdout, result.stderr


def execute_commit(message):
    """Execute git commit with message.

    Args:
        message: Complete commit message

    Returns:
        tuple: (returncode, stdout, stderr)
    """
    code, stdout, stderr = run_command(["git", "commit", "-m", message])
    return code, stdout, stderr


def main():
    """Main entry point for git commit tool."""
    print("Git Commit Tool")
    print("=" * 40)

    # Step 1: Check staged changes
    print("\n[1/4] Checking staged changes...")
    files = check_staged_changes()

    if files is None:
        print("ERROR: No changes staged for commit.", file=sys.stderr)
        print("Run 'git add <files>' to stage changes first.", file=sys.stderr)
        return 1

    print(f"Found {len(files)} staged file(s):")
    for f in files:
        print(f"  - {f}")

    # Step 2: Atomic commit analysis
    print("\n[2/4] Analyzing commit atomicity...")
    result = analyze_atomicity(files)

    if not result["is_atomic"]:
        print(f"WARNING: {result['warning']}", file=sys.stderr)
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Commit aborted. Consider splitting into smaller commits.")
            return 1
    else:
        print("OK: Commit appears atomic")

    # Step 3: Generate commit message
    print("\n[3/4] Generating commit message...")
    diff = get_staged_diff()

    # Try LLM generation
    message = generate_with_llm(diff)

    if message:
        print("\nLLM-generated message:")
        print("-" * 40)
        print(message)
        print("-" * 40)

        response = input("\nUse this message? (y/n/edit): ").lower()
        if response == 'n':
            print("\n")
            message = get_manual_commit_message()
        elif response == 'edit':
            print("\nEditing - enter new message:")
            message = get_manual_commit_message()

        if message is None:
            print("Commit cancelled.")
            return 1
    else:
        # Fall back to manual input
        print("LLM not available. Enter message manually:")
        message = get_manual_commit_message()
        if message is None:
            print("Commit cancelled.")
            return 1

    # Validate subject
    subject_line = message.split("\n")[0]
    errors = validate_subject(subject_line)

    if errors:
        print("\nWARNING: Subject line issues:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return 1

    # Show preview
    print("\nCommit message preview:")
    print("-" * 40)
    print(message)
    print("-" * 40)

    response = input("\nProceed with commit? (y/N): ")
    if response.lower() != 'y':
        print("Commit cancelled.")
        return 1

    # Step 4: Execute commit
    print("\n[4/4] Executing commit...")
    code, stdout, stderr = execute_commit(message)

    if code != 0:
        print(f"Commit failed: {stderr}", file=sys.stderr)
        return 1

    print("Commit successful!")
    if stdout:
        print(stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
