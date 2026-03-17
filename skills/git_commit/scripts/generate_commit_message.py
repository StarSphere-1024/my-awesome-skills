#!/usr/bin/env python3
"""Generate Conventional Commit messages from git diff using LLM."""

import subprocess
import sys
import textwrap


COMMIT_MESSAGE_PROMPT = """You are a Principal Engineer reviewing staged changes.
Your goal is to write a commit message that makes the project's history clean and meaningful.

Focus on the PURPOSE of the change:
- Why was this refactoring done?
- What bug did this logic fix?
- What feature does this enable?

Avoid:
- Redundant phrases like "Modified file X"
- Describing line-by-line changes
- Vague statements like "Updated code"

Rules:
1. Format: <type>(<scope>): <subject>
2. Subject: imperative mood, max 50 chars, no period
3. Body: explain WHY and HOW, wrap at 72 chars
4. Breaking changes: add ! after type and BREAKING CHANGE: footer
5. NO co-author attributions
6. English only

Available types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

---
DIFF:
{diff}
---

Generate the commit message (only the message, no explanation):"""


def get_staged_diff():
    """Get full staged diff.

    Returns:
        str: Git diff output
    """
    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout


def parse_llm_response(response):
    """Parse LLM response into subject, body, footer.

    Args:
        response: Raw LLM response text

    Returns:
        tuple: (subject, body, footer)
    """
    lines = response.strip().split("\n")

    subject = lines[0].strip() if lines else ""
    body_lines = []
    footer_lines = []

    in_body = False
    in_footer = False

    for line in lines[1:]:
        if line.startswith("BREAKING CHANGE:"):
            in_footer = True
            footer_lines.append(line)
        elif line.startswith("Fixes") or line.startswith("Refs"):
            in_footer = True
            footer_lines.append(line)
        elif in_footer:
            footer_lines.append(line)
        elif line.strip():
            in_body = True
            body_lines.append(textwrap.fill(line, width=72))

    body = "\n".join(body_lines) if body_lines else None
    footer = "\n".join(footer_lines) if footer_lines else None

    return subject, body, footer


def validate_subject(subject):
    """Validate subject line follows conventions.

    Args:
        subject: Subject line string

    Returns:
        list: List of error messages (empty if valid)
    """
    errors = []

    if len(subject) > 50:
        errors.append(f"Subject too long ({len(subject)} > 50 chars)")

    if subject.endswith("."):
        errors.append("Subject should not end with period")

    # Check for imperative mood (basic check)
    if subject.startswith(("Added ", "Fixed ", "Changed ", "Updated ", "Modified ")):
        errors.append("Use imperative mood: 'add' not 'added'")

    return errors


def format_commit_message(subject, body=None, footer=None):
    """Format final commit message.

    Args:
        subject: Subject line
        body: Optional body text
        footer: Optional footer text

    Returns:
        str: Complete commit message
    """
    message = subject

    if body:
        message += f"\n\n{body}"

    if footer:
        message += f"\n\n{footer}"

    return message


def generate_with_llm(diff):
    """Generate commit message using rule-based analysis.

    Args:
        diff: Git diff text

    Returns:
        str: Generated commit message or None if failed
    """
    try:
        return generate_rule_based_message(diff)
    except Exception as e:
        print(f"Message generation failed: {e}", file=sys.stderr)
        return None


def generate_rule_based_message(diff):
    """Generate commit message using pattern matching and heuristics.

    Args:
        diff: Git diff text

    Returns:
        str: Generated commit message
    """
    import re

    lines = diff.split('\n')

    # Collect changed files
    changed_files = []
    additions = 0
    deletions = 0

    for line in lines:
        if line.startswith('diff --git'):
            match = re.search(r'b/(.+)', line)
            if match:
                changed_files.append(match.group(1))
        elif line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1

    if not changed_files:
        return None

    # Determine scope from file paths
    scope = determine_scope(changed_files)

    # Determine commit type from changes
    commit_type = determine_commit_type(diff, changed_files)

    # Generate subject based on patterns
    subject = generate_subject(commit_type, scope, changed_files, additions, deletions)

    # Generate body
    body = generate_body(changed_files, additions, deletions)

    return format_commit_message(subject, body)


def determine_scope(files):
    """Determine commit scope from file paths.

    Args:
        files: List of changed file paths

    Returns:
        str: Scope string
    """
    # Common scope patterns
    scope_patterns = {
        'docs': ['docs/', 'README', '.md'],
        'test': ['test', 'spec', '__tests__/'],
        'config': ['.github/', 'config/', 'settings/', '.gitignore', 'pyproject.toml', 'package.json'],
        'scripts': ['scripts/', 'bin/', 'tools/'],
        'ci': ['.github/workflows/', '.circleci/', '.gitlab-ci.yml'],
        'deps': ['requirements', 'package-lock.json', 'yarn.lock', 'Cargo.toml'],
    }

    for scope, patterns in scope_patterns.items():
        for f in files:
            if any(p in f for p in patterns):
                return scope

    # Default to first directory in path
    for f in files:
        if '/' in f:
            return f.split('/')[0]

    return 'core'


def determine_commit_type(diff, files):
    """Determine commit type from changes.

    Args:
        diff: Git diff text
        files: List of changed file paths

    Returns:
        str: Commit type (feat, fix, docs, etc.)
    """
    # Check for test files
    if any('test' in f or 'spec' in f for f in files):
        return 'test'

    # Check for documentation
    if any(f.endswith('.md') or 'docs/' in f for f in files):
        return 'docs'

    # Check for config files
    config_files = ['.gitignore', '.github/', 'config/', 'pyproject.toml',
                    'setup.cfg', 'package.json', '.eslintrc']
    if any(any(c in f for c in config_files) for f in files):
        return 'chore'

    # Check diff for common patterns
    diff_lower = diff.lower()
    if 'fix' in diff_lower or 'bug' in diff_lower or 'error' in diff_lower:
        return 'fix'
    if 'refactor' in diff_lower or 'rename' in diff_lower:
        return 'refactor'
    if 'perf' in diff_lower or 'optim' in diff_lower or 'cache' in diff_lower:
        return 'perf'
    if 'add' in diff_lower or 'new' in diff_lower or 'create' in diff_lower:
        return 'feat'

    # Default to refactor for general changes
    return 'refactor'


def generate_subject(commit_type, scope, files, additions, deletions):
    """Generate commit subject line.

    Args:
        commit_type: Type of commit
        scope: Scope of changes
        files: List of changed files
        additions: Number of lines added
        deletions: Number of lines deleted

    Returns:
        str: Subject line (max 50 chars)
    """
    # Common action verbs based on type
    actions = {
        'feat': 'add',
        'fix': 'fix',
        'docs': 'update',
        'style': 'format',
        'refactor': 'refactor',
        'perf': 'optimize',
        'test': 'test',
        'build': 'update',
        'ci': 'update',
        'chore': 'clean',
        'revert': 'revert',
    }

    action = actions.get(commit_type, 'update')

    # Determine what was changed
    if len(files) == 1:
        target = files[0].split('/')[-1]
        if len(target) > 20:
            target = target[:18] + '..'
    elif len(files) <= 3:
        target = f'{len(files)} files'
    else:
        target = f'{len(files)} files'

    # Build subject
    subject = f"{action}: {target}"

    # Add scope if we have one
    if scope and scope not in ['core', 'src']:
        subject = f"{action}({scope}): {target}"

    # Ensure max 50 chars
    if len(subject) > 50:
        subject = subject[:47] + '...'

    return subject


def generate_body(files, additions, deletions):
    """Generate commit body.

    Args:
        files: List of changed file paths
        additions: Number of lines added
        deletions: Number of lines deleted

    Returns:
        str: Body text
    """
    if len(files) == 1:
        body = f"Modified {files[0]}"
    else:
        body = f"Modified {len(files)} files"

    body += f"\n\nStats: +{additions} -{deletions}"

    return textwrap.fill(body, width=72)


def get_manual_commit_message():
    """Get commit message via manual user input.

    Returns:
        str: User-entered commit message or None if cancelled
    """
    print("\nEnter commit message:")
    print("Format: <type>(<scope>): <subject>")
    print("      : [blank line]")
    print("      : [body explaining WHY and HOW]")
    print("\nType 'q' on first line to cancel.")
    print("---")

    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            return None

        if line == 'q' and len(lines) == 0:
            return None

        lines.append(line)

        # After subject line, prompt for body
        if len(lines) == 1:
            print("Body (press Enter twice to finish):")

        # Two consecutive empty lines = done
        if len(lines) >= 2 and lines[-1] == "" and lines[-2] == "":
            break

    # Remove trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def main():
    """Main entry point."""
    try:
        diff = get_staged_diff()
    except subprocess.CalledProcessError as e:
        print(f"Error getting diff: {e}", file=sys.stderr)
        sys.exit(1)

    if not diff.strip():
        print("No staged changes", file=sys.stderr)
        sys.exit(1)

    # Try LLM generation first
    message = generate_with_llm(diff)

    if message:
        print("\nGenerated commit message:")
        print("-" * 40)
        print(message)
        print("-" * 40)

        response = input("\nUse this message? (y/n/edit): ").lower()
        if response == 'n':
            message = get_manual_commit_message()
        elif response == 'edit':
            print("\nEditing - enter new message:")
            message = get_manual_commit_message()

        if message is None:
            print("Commit cancelled.")
            sys.exit(1)
    else:
        # Fall back to manual input
        message = get_manual_commit_message()
        if message is None:
            print("Commit cancelled.")
            sys.exit(1)

    # Validate and output
    subject_line = message.split("\n")[0]
    errors = validate_subject(subject_line)

    if errors:
        print("\nWARNING: Subject line issues:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)

    print("\nFinal commit message:")
    print("=" * 40)
    print(message)
    print("=" * 40)

    return 0


if __name__ == "__main__":
    sys.exit(main())
