# Docker Image Validation - Detailed Examples

This document contains comprehensive examples and detailed implementations for Docker image validation patterns, extracted from CLAUDE.md for reference.

## Essential Validation Pattern

**MANDATORY fail-fast validation for Docker image availability to prevent silent E2E test failures.**

**THE PROBLEM**: Multi-line Docker image tags from docker/metadata-action cause E2E validation to check wrong tags, leading to silent test skipping instead of clear failures.

### Event-Aware Tag Selection with Fail-Fast Validation

```yaml
# Event-aware tag selection with fail-fast validation
extract_image_tag() {
  local full_output="$1"
  case "${{ github.event_name }}" in
    "workflow_dispatch") selected_tag=$(echo "$full_output" | tail -n1) ;;  # SHA-based
    "pull_request"|"push") selected_tag=$(echo "$full_output" | head -n1) ;;  # PR/latest
  esac
  echo "$selected_tag"
}

# FAIL-FAST validation
if ! docker manifest inspect "$IMAGE_TAG" > /dev/null 2>&1; then
  echo "❌ CRITICAL: Image not found: $IMAGE_TAG (Event: ${{ github.event_name }})"
  exit 1  # FAIL THE JOB - Don't skip silently!
fi
```

## Key Requirements

- Multi-line tag detection with event-aware selection
- `exit 1` on validation failure (never silent skip)
- Clear error reporting with event context

This comprehensive validation approach ensures Docker images are available and properly formatted before use in E2E testing, preventing silent failures and providing clear error context for debugging.