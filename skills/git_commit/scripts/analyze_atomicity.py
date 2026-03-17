#!/usr/bin/env python3
"""Analyze if staged changes represent an atomic commit."""

import sys
from collections import Counter


# Domain mapping - group related directories
DOMAIN_PATTERNS = {
    "database": ["database/", "db/", "migrations/", "models/"],
    "backend": ["src/", "api/", "backend/", "server/"],
    "frontend": ["frontend/", "ui/", "components/", "pages/", "src/"],
    "docs": ["docs/", "documentation/", "README", "*.md"],
    "config": ["config/", "settings/", ".github/", ".gitignore"],
    "tests": ["tests/", "test/", "specs/", "__tests__/"],
    "scripts": ["scripts/", "bin/", "tools/"],
}


def detect_domain(filepath):
    """Detect which domain a file belongs to.

    Args:
        filepath: Path to the file

    Returns:
        str: Domain name or 'other' if no match
    """
    for domain, patterns in DOMAIN_PATTERNS.items():
        for pattern in patterns:
            if pattern.endswith("/"):
                if filepath.startswith(pattern):
                    return domain
            elif pattern.startswith("*."):
                if filepath.endswith(pattern[1:]):
                    return domain
            else:
                if pattern in filepath:
                    return domain
    return "other"


def analyze_atomicity(files):
    """Analyze if files represent an atomic commit.

    Args:
        files: List of file paths

    Returns:
        dict with 'is_atomic' (bool) and 'warning' (str or None)
    """
    if not files:
        return {"is_atomic": True, "warning": None}

    domains = [detect_domain(f) for f in files]
    domain_counts = Counter(domains)

    # Count distinct non-other domains
    significant_domains = [d for d, c in domain_counts.items()
                         if d != "other" and c >= 1]

    # Warn if 3+ distinct domains are modified
    if len(significant_domains) >= 3:
        return {
            "is_atomic": False,
            "warning": f"This commit seems non-atomic. Consider splitting it into smaller commits. Domains detected: {', '.join(significant_domains)}"
        }

    return {"is_atomic": True, "warning": None}


def main():
    """Entry point - analyze files from stdin or args."""
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = [line.strip() for line in sys.stdin if line.strip()]

    result = analyze_atomicity(files)

    if result["warning"]:
        print(result["warning"], file=sys.stderr)
        sys.exit(1)

    print("OK: Commit appears atomic")
    sys.exit(0)


if __name__ == "__main__":
    main()
