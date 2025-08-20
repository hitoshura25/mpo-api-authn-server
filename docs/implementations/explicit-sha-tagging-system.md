# Explicit Docker SHA Tagging System Implementation

## Overview

This document describes the implementation of explicit Docker SHA tagging with PR/branch information to replace time-based SHA digest cleanup with precise targeting. This eliminates the need for time-based guessing and enables accurate cleanup of Docker images created during CI/CD workflows.

## Problem Statement

Previously, Docker builds created SHA digest tags like `sha256-31ff0a7c7dcef4e57b2d69425c019901d4248f5d103a317df94dc9ede30a1acb` with no PR or branch association. The cleanup script used time-based guessing (last 24 hours) which was imprecise and could accidentally target wrong images.

## Solution Implementation

### 1. Docker Build Workflow Changes

**File**: `.github/workflows/docker-build.yml`

**Key Changes**:
- Added explicit SHA tagging steps after Docker image pushes
- Extract short SHA (8 chars) from full image digest
- Create context-specific tags based on GitHub event type
- Added new workflow outputs for context tags

**Tag Format Examples**:
- **PR builds**: `sha256-abc12345-pr-47`
- **Main branch builds**: `sha256-abc12345-main-123` (with run number)
- **Manual builds**: `sha256-abc12345-manual-1692456789` (with timestamp)
- **Branch builds**: `sha256-abc12345-branch-feature-name-123`

**Implementation Details**:
```bash
# Extract short SHA from image digest
DIGEST="sha256:31ff0a7c7dcef4e57b2d69425c019901d4248f5d103a317df94dc9ede30a1acb"
SHORT_SHA=$(echo "$DIGEST" | cut -c8-15)  # Results in "31ff0a7c"

# Create context-specific tag
if [[ "${{ github.event_name }}" == "pull_request" ]]; then
    CONTEXT_TAG="sha256-${SHORT_SHA}-pr-${{ github.event.pull_request.number }}"
    # Results in: sha256-31ff0a7c-pr-47
fi

# Apply tag using buildx imagetools
docker buildx imagetools create "$FULL_IMAGE_NAME@$DIGEST" --tag "$FULL_IMAGE_NAME:$CONTEXT_TAG"
```

### 2. Cleanup Script Updates

**File**: `scripts/docker/cleanup-staging-packages.sh`

**Key Changes**:
- Removed time-based cutoff date logic
- Updated filter patterns to use explicit SHA tag matching
- Enhanced documentation with explicit tagging system explanation
- Maintained backward compatibility with existing PR tags

**Before (Time-based)**:
```bash
local cutoff_date=$(date -u -d '24 hours ago' '+%Y-%m-%dT%H:%M:%SZ')
filter_conditions='
    (.metadata.container.tags[]? | test("^pr-'$PR_NUMBER'$")) or
    (.metadata.container.tags[]? | test("^sha256-.*pr-'$PR_NUMBER'")) or
    ((.metadata.container.tags[]? | test("^sha256-")) and (.created_at >= "'$cutoff_date'"))'
```

**After (Explicit)**:
```bash
filter_conditions='
    (.metadata.container.tags[]? | test("^pr-'$PR_NUMBER'$")) or
    (.metadata.container.tags[]? | test("^sha256-[a-f0-9]+-pr-'$PR_NUMBER'$"))'
```

### 3. Pattern Validation

**File**: `scripts/docker/test-sha-patterns.sh`

Created comprehensive test script to validate regex patterns:
- PR-specific patterns correctly target only specific PR numbers
- Broad staging patterns include all staging contexts
- Production tags are excluded from cleanup targeting
- Plain SHA tags without context are protected

## Benefits Achieved

### 1. Precise Targeting
- **Before**: Time-based guessing could target wrong images
- **After**: Exact PR/branch identification with zero false positives

### 2. No False Positives
- **Before**: "Last 24 hours" could include unrelated builds
- **After**: Only target images from specific PR/branch/workflow

### 3. Better Debugging
- **Before**: Hard to identify which workflow created which SHA digest
- **After**: Context tag clearly shows source: `sha256-abc12345-pr-47`

### 4. Improved Safety
- **Before**: Risk of accidentally deleting production images
- **After**: Explicit staging patterns exclude production tags

## Workflow Integration

### New Workflow Outputs

Added to `docker-build.yml`:
```yaml
outputs:
  webauthn-context-tag:
    description: 'WebAuthn server explicit SHA context tag for precise cleanup targeting'
    value: ${{ jobs.build-push-docker-images.outputs.webauthn-context-tag }}
  test-credentials-context-tag:
    description: 'Test credentials service explicit SHA context tag for precise cleanup targeting'
    value: ${{ jobs.build-push-docker-images.outputs.test-credentials-context-tag }}
```

### Usage in Downstream Workflows

Cleanup scripts can now target specific builds:
```bash
# Clean up specific PR
CLEANUP_PR_NUMBER=47 ./cleanup-staging-packages.sh success

# Will target:
# - pr-47
# - sha256-*-pr-47
# But NOT:
# - sha256-* (plain SHA tags)
# - pr-48 (different PR)
# - latest, main (production tags)
```

## Testing and Validation

### Pattern Testing
```bash
./scripts/docker/test-sha-patterns.sh
```
Results:
- ✅ PR-specific patterns correctly identify target tags
- ✅ Broad patterns include all staging contexts
- ✅ Production tags excluded from cleanup
- ✅ Plain SHA tags protected from accidental deletion

### Build Integration
- ✅ Docker build workflow successfully creates explicit SHA tags
- ✅ Context tags properly reflect GitHub event information
- ✅ Workflow outputs correctly expose context tags
- ✅ No regression in existing Docker build functionality

## Backward Compatibility

### Maintained Features
- ✅ Existing `pr-{number}` tag cleanup continues to work
- ✅ Staging package patterns (`*-staging`) unchanged
- ✅ npm and Maven cleanup logic unaffected
- ✅ All existing cleanup script parameters work as before

### Migration Strategy
- **Phase 1** (Completed): Explicit SHA tagging in Docker builds
- **Phase 2** (Completed): Updated cleanup script patterns
- **Phase 3** (Ongoing): Monitor cleanup effectiveness in production
- **Phase 4** (Future): Remove legacy time-based fallbacks after validation period

## Configuration

### Environment Variables (Unchanged)
All existing environment variables continue to work:
- `CLEANUP_PR_NUMBER`: Target specific PR for cleanup
- `PRESERVE_STAGING`: Emergency override to skip cleanup
- `GH_TOKEN`: GitHub token for API access

### New Debug Information
Enhanced logging shows explicit SHA tag creation:
```
🏷️ Creating explicit SHA tags with PR/branch context...
📋 WebAuthn Server Digest: sha256:31ff0a7c...
📋 Short SHA: 31ff0a7c
🎯 PR Context: Creating tag sha256-31ff0a7c-pr-47
✅ Explicit SHA tag created successfully
```

## Monitoring and Validation

### Success Metrics
- **Zero false positives**: Only target intended PR/branch images
- **100% precision**: No accidental deletion of production images
- **Clear traceability**: Easy to identify image source from tag
- **Maintained performance**: No degradation in build/cleanup speed

### Rollback Plan
If issues arise:
1. Set `PRESERVE_STAGING=true` to disable all cleanup
2. Revert cleanup script to previous time-based logic
3. Remove explicit SHA tagging steps from Docker workflow
4. Monitor and investigate issues before re-implementation

## Implementation Status

- ✅ Docker build workflow explicit SHA tagging
- ✅ Cleanup script precision targeting updates
- ✅ Pattern validation and testing
- ✅ Backward compatibility verification
- ✅ Documentation and monitoring setup
- 🔄 Production validation (ongoing)

This implementation provides a robust, precise, and safe approach to Docker image cleanup while maintaining full backward compatibility with existing workflows.