# Bash Function Output Redirection - Detailed Examples

This document contains comprehensive examples for bash function output redirection patterns, extracted from CLAUDE.md for reference.

## Essential Pattern

**MANDATORY output redirection for bash functions that return values to prevent debug pollution.**

**THE PROBLEM**: Bash functions with debug output pollute captured return values, causing failures with multi-line variable assignments.

### Essential Pattern:
```bash
# ❌ WRONG: Debug output goes to stdout
extract_value() {
  echo "🔧 Processing..."     # Pollutes output!
  echo "$final_result"        # What we want
}

# ✅ CORRECT: Debug to stderr, result to stdout
extract_value() {
  echo "🔧 Processing..." >&2  # Debug to stderr
  echo "$final_result"         # Only result to stdout
}

RESULT=$(extract_value "input")  # Captures only final_result
```

## Key Rules

- **Debug/status messages**: `echo "Debug" >&2`
- **Return value**: `echo "$result"` (no redirection)
- **Always test**: `RESULT=$(func); echo "Got: '$RESULT'"`

This pattern ensures clean function outputs and prevents debug pollution in captured values.