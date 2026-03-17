#!/usr/bin/env python3
"""Check for staged git changes and return file list or None."""

import subprocess
import sys


def check_staged_changes():
    """Check for staged changes using git diff --cached --name-only.

    Returns:
        list: List of staged file paths, or None if no changes staged.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            return result.stdout.strip().split("\n")
        return None
    except subprocess.CalledProcessError:
        return None


def main():
    """Entry point - print staged files or exit with error."""
    files = check_staged_changes()

    if files is None:
        print("ERROR: No changes staged for commit.", file=sys.stderr)
        print("Run 'git add <files>' to stage changes first.", file=sys.stderr)
        sys.exit(1)

    for f in files:
        print(f)
    sys.exit(0)


if __name__ == "__main__":
    main()
