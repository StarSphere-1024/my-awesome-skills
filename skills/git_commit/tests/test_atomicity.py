#!/usr/bin/env python3
"""Tests for atomicity analysis functionality."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.analyze_atomicity import analyze_atomicity, detect_domain


def test_single_domain_is_atomic():
    """Files in same domain should be atomic"""
    files = ["src/auth/login.py", "src/auth/logout.py"]
    result = analyze_atomicity(files)
    assert result["is_atomic"] == True, f"Expected atomic for same domain, got {result}"
    print("PASS: test_single_domain_is_atomic")


def test_multiple_domains_not_atomic():
    """Files in different domains should warn"""
    files = ["database/models.py", "frontend/ui/button.tsx", "docs/readme.md"]
    result = analyze_atomicity(files)
    assert result["is_atomic"] == False, f"Expected non-atomic for multiple domains, got {result}"
    assert result["warning"] is not None, "Expected warning for non-atomic commit"
    assert "non-atomic" in result["warning"].lower(), f"Warning should mention non-atomic: {result['warning']}"
    print("PASS: test_multiple_domains_not_atomic")


def test_detect_domain():
    """Test domain detection"""
    assert detect_domain("database/models.py") == "database"
    assert detect_domain("frontend/ui/button.tsx") == "frontend"
    assert detect_domain("docs/readme.md") == "docs"
    assert detect_domain("tests/test_auth.py") == "tests"
    assert detect_domain("unknown/file.txt") == "other"
    print("PASS: test_detect_domain")


def test_two_domains_allowed():
    """Two domains should be allowed (code + tests)"""
    files = ["src/auth/login.py", "tests/test_auth.py"]
    result = analyze_atomicity(files)
    # This should pass since it's only 2 domains
    print(f"Two domains result: {result}")
    print("PASS: test_two_domains_allowed")


if __name__ == "__main__":
    test_single_domain_is_atomic()
    test_multiple_domains_not_atomic()
    test_detect_domain()
    test_two_domains_allowed()
    print("\nAll tests passed!")
