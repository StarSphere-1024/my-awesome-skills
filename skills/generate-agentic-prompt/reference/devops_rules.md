# DevOps/SRE Infrastructure Rules

## Core Principle

**Infrastructure code MUST be safe by default, idempotent, and self-cleaning.** Every script is a production artifact that may run unattended at 3 AM. Write accordingly.

---

## 1. Strict Idempotency (绝对幂等性)

**Rule:** Scripts MUST produce identical results regardless of how many times they execute.

### Required Patterns

```sh
# ❌ BAD: Fails on second run
mkdir /var/lib/myapp

# ✅ GOOD: Check state first
if [ ! -d "/var/lib/myapp" ]; then
    mkdir -p /var/lib/myapp
fi

# ❌ BAD: Blindly appends, creates duplicates
echo "server=localhost:8080" >> /etc/myapp/config.conf

# ✅ GOOD: Check before modifying
if ! grep -q "server=localhost:8080" /etc/myapp/config.conf 2>/dev/null; then
    echo "server=localhost:8080" >> /etc/myapp/config.conf
fi

# ❌ BAD: Always restarts service
systemctl restart myapp

# ✅ GOOD: Restart only if config changed or service not running
if ! systemctl is-active --quiet myapp || [ "$CONFIG_CHANGED" = "true" ]; then
    systemctl restart myapp
fi
```

### Forbidden Operations

- Blind `>>` appends without existence checks
- Unconditional service restarts
- `rm -rf` without explicit path validation
- Database operations without `IF NOT EXISTS` / `IF EXISTS` clauses

---

## 2. POSIX Compliance & Standard Streams (标准流与跨平台)

**Rule:** Separation of concerns through proper stream usage enables reliable automation.

### Stream Discipline

| Stream | Use For | Example |
|--------|---------|---------|
| `stdout` | Machine-readable output, data results | Query results, parsed values |
| `stderr` | All logs, warnings, errors, progress | `log "Starting deployment..."` |
| Exit code | Success/failure signaling | `0` = success, `1+` = failure |

### Implementation

```sh
# ✅ Logging functions
log() {
    echo "[INFO] $*" >&2
}

warn() {
    echo "[WARN] $*" >&2
}

die() {
    echo "[FATAL] $*" >&2
    exit "${2:-1}"
}

# ✅ Data output (to stdout)
get_service_port() {
    local port
    port=$(grep "^port=" /etc/myapp/config.conf 2>/dev/null | cut -d= -f2)
    if [ -z "$port" ]; then
        die "Port not configured" 1
    fi
    echo "$port"  # Machine-readable to stdout
}

# ✅ POSIX-compliant conditionals
if [ -n "${VAR:-}" ]; then   # Not empty (works in sh)
    :
fi

if command -v curl >/dev/null 2>&1; then   # Check command exists
    :
fi
```

### Exit Code Standards

```sh
# Standard exit codes
EXIT_SUCCESS=0
EXIT_FAILURE=1
EXIT_USAGE=64      # Command line usage error
EXIT_NOUSER=67     # Addressee unknown (user not found)
EXIT_NOHOST=68     # Hostname unknown
EXIT_UNAVAILABLE=69 # Service unavailable
EXIT_SOFTWARE=70   # Internal software error
EXIT_OS=71         # Operating system error
EXIT_CONFIG=78     # Configuration error
```

---

## 3. Graceful Degradation & Cleanup (优雅清理)

**Rule:** Scripts MUST leave no traces and release all resources on any exit path.

### Trap Pattern

```sh
#!/bin/sh

# Temporary file management
TMPDIR="${TMPDIR:-/tmp}"
TMP_FILE=$(mktemp "${TMPDIR}/myapp.XXXXXX")

# Cleanup handler
cleanup() {
    local exit_code=$?
    rm -f "$TMP_FILE"
    rm -rf "${TMP_FILE}.d" 2>/dev/null
    # Release locks, kill background jobs
    if [ -n "${LOCK_FD:-}" ]; then
        flock -u "$LOCK_FD" 2>/dev/null || true
    fi
    exit "$exit_code"
}

# Register cleanup on EXIT, INT, TERM, HUP
trap cleanup EXIT INT TERM HUP

# Create lock file
LOCK_FILE="${TMPDIR}/myapp.lock"
exec {LOCK_FD}>"$LOCK_FILE"
if ! flock -n "$LOCK_FD"; then
    die "Another instance is running (lock: $LOCK_FILE)" 1
fi

# Main logic continues...
```

### Signal Handling Best Practices

```sh
# ✅ Graceful shutdown flag
SHUTDOWN_REQUESTED=false

handle_shutdown() {
    warn "Shutdown requested, finishing current operation..."
    SHUTDOWN_REQUESTED=true
}

trap handle_shutdown INT TERM

# In long-running loops
while [ "$SHUTDOWN_REQUESTED" = "false" ]; do
    process_batch
    sleep 1
done

log "Graceful shutdown complete"
```

---

## 4. Dry-Run Capability (预演模式)

**Rule:** Any destructive operation MUST support `--dry-run` that shows intent without execution.

### Implementation Pattern

```sh
#!/bin/sh

DRY_RUN=false

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --dry-run|-n)
                DRY_RUN=true
                log "Dry-run mode ENABLED - no changes will be made"
                ;;
            --force)
                FORCE=true
                ;;
            -*)
                die "Unknown option: $1" 64
                ;;
        esac
        shift
    done
}

# Execute or simulate
execute() {
    if [ "$DRY_RUN" = "true" ]; then
        log "[DRY-RUN] Would execute: $*"
        return 0
    fi
    log "Executing: $*"
    eval "$@"
}

# Usage examples
execute "rm -rf /var/cache/myapp/*"
execute "systemctl restart myapp"
execute "mysql -e 'DROP TABLE temp_data'"

# Destructive operation with confirmation
destructive_operation() {
    if [ "$DRY_RUN" = "true" ]; then
        log "[DRY-RUN] Would DELETE: $1"
        return 0
    fi

    if [ "${FORCE:-false}" != "true" ]; then
        printf "[CONFIRM] Delete %s? [y/N] " "$1" >&2
        read -r response
        case "$response" in
            [yY][eE][sS]|[yY])
                :
                ;;
            *)
                log "Aborted by user"
                return 1
                ;;
        esac
    fi

    rm -rf "$1"
}
```

### Dry-Run Output Format

```
[DRY-RUN] Would create directory: /var/lib/myapp/data
[DRY-RUN] Would modify file: /etc/myapp/config.conf
  - Remove: old_setting=value
  - Add: new_setting=value
[DRY-RUN] Would restart service: myapp
[DRY-RUN] Would delete 3 files from /tmp (15MB total)
```

---

## 5. Fail-Safe Execution (安全执行模式)

**Rule:** Bash scripts MUST enforce strict mode. Silent failures are infrastructure debt.

### Strict Mode Header

```sh
#!/bin/bash
set -euo pipefail

# Optional: Debug mode when MYAPP_DEBUG=1
if [ "${MYAPP_DEBUG:-}" = "1" ]; then
    set -x
fi

# Optional: Custom error handler
error_handler() {
    local exit_code=$?
    local line_number=$1
    die "Script failed at line ${line_number} with exit code ${exit_code}" "$exit_code"
}

trap 'error_handler ${LINENO}' ERR
```

### Understanding `set -euo pipefail`

| Flag | Effect | Why Required |
|------|--------|--------------|
| `-e` | Exit immediately on command failure | Prevents cascading errors |
| `-u` | Treat unset variables as errors | Catches typos, missing env vars |
| `-o pipefail` | Pipeline fails if any command fails | Prevents masked errors in pipes |

### Safe Variable Handling

```sh
# ❌ BAD: Silent if VAR is unset
echo "$VAR"

# ✅ GOOD: Error if VAR is unset
echo "${VAR}"  # -u flag catches this

# ✅ GOOD: Provide default
echo "${VAR:-default_value}"

# ✅ GOOD: Error with custom message if unset
: "${VAR:?VAR environment variable is required}"

# ✅ GOOD: Check before use
if [ -n "${VAR:-}" ]; then
    :
fi
```

### Safe Command Patterns

```sh
# ❌ BAD: Silent failure, continues with wrong state
grep "pattern" file.txt | process_output

# ✅ GOOD: Explicit about optional success
if grep "pattern" file.txt | process_output; then
    log "Pattern found and processed"
else
    log "Pattern not found (non-fatal)"
fi

# ❌ BAD: May delete wrong directory if VAR empty
rm -rf "$MYAPP_DIR"/*

# ✅ GOOD: Validate before destructive operation
if [ -z "${MYAPP_DIR:-}" ]; then
    die "MYAPP_DIR is not set" 78
fi
if [ "${MYAPP_DIR}" = "/" ] || [ "${MYAPP_DIR}" = "/etc" ]; then
    die "Refusing to delete from protected path: $MYAPP_DIR" 1
fi
rm -rf "$MYAPP_DIR"/*
```

---

## Quick Reference Checklist

Before running any infrastructure script:

- [ ] **Idempotent?** Safe to run twice, won't corrupt state
- [ ] **Streams correct?** Data→stdout, logs→stderr
- [ ] **Exit codes?** Returns 0 on success, appropriate code on failure
- [ ] **Cleanup registered?** `trap cleanup EXIT INT TERM HUP`
- [ ] **Temp files tracked?** All `/tmp` usage cleaned on exit
- [ ] **Dry-run available?** Destructive ops support `--dry-run`
- [ ] **Strict mode?** `set -euo pipefail` at top
- [ ] **Variables validated?** No unbound variable errors
- [ ] **Paths validated?** No accidental `/` deletions

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Script fails silently mid-execution | Add `set -e` and error trap |
| Second run corrupts config | Add existence checks before mutations |
| No way to preview changes | Implement `--dry-run` flag |
| Temp files accumulate in `/tmp` | Use `trap cleanup EXIT` |
| Logs mixed with data output | Separate stdout (data) and stderr (logs) |
| Script continues after critical failure | Check exit codes explicitly |
| Unset variables become empty strings | Use `set -u` and `${VAR:?message}` |

---

## Enforcement

Violating these rules creates infrastructure debt. Every violation is a future incident waiting to happen.

**Violating the letter of these rules is violating the spirit of infrastructure safety.**
