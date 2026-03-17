# Conventional Commits Reference

## Format

```
<type>(<scope>): <subject>
```

or with breaking change:

```
<type>(<scope>)!: <subject>
```

## Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code style (no logic change) |
| `refactor` | Code refactoring (no bug fix/feature) |
| `perf` | Performance improvement |
| `test` | Test additions/corrections |
| `build` | Build system/dependencies |
| `ci` | CI configuration |
| `chore` | Maintenance/misc |
| `revert` | Revert previous commit |

## Rules

1. **Subject line**:
   - Imperative mood: "fix" not "fixed" or "fixing"
   - Max 50 characters
   - No period at end
   - Lowercase after type

2. **Body** (optional):
   - Blank line after subject
   - Explain WHY and HOW
   - Wrap at 72 characters

3. **Breaking changes**:
   - Add `!` after type/scope
   - Include `BREAKING CHANGE:` footer

4. **Footers**:
   - No co-author attributions
   - Issue references optional
