# Debugging Staging Cleanup Script Failures

## Problem Summary

The staging cleanup script (`scripts/docker/cleanup-staging-packages.sh`) was successfully finding and filtering packages but failing during the deletion phase with exit code 1 and no specific error details.

## Enhanced Debugging Features Added

### 1. Comprehensive Error Logging

**Enhanced deletion loops** in all package types (Docker, npm, Maven) now provide:
- Detailed API endpoint logging
- HTTP status code analysis  
- Specific error message capture
- Exit code tracking
- Continue-on-error logic to prevent script termination

### 2. Authentication Validation

**Improved `validate_github_cli()` function** includes:
- Detailed GitHub CLI auth status output
- API access testing with user information
- Token environment variable validation
- Permission requirement guidance

### 3. Manual Testing Mode

**New manual testing capability** allows isolated testing:
```bash
# Test specific version deletion
./cleanup-staging-packages.sh test "/users/username/packages/container/webauthn-server" "490951546"
```

### 4. Quick Test Script

**Created `test-delete-version.sh`** for rapid debugging:
```bash
# Test the exact failing deletion command
./scripts/docker/test-delete-version.sh 490951546
```

## Debugging Workflow

### Step 1: Use Quick Test Script
```bash
cd /Users/vinayakmenon/mpo-api-authn-server
./scripts/docker/test-delete-version.sh 490951546
```

### Step 2: If Quick Test Fails, Use Manual Mode
```bash
./scripts/docker/cleanup-staging-packages.sh test "/users/hitoshura25/packages/container/webauthn-server" "490951546"
```

### Step 3: Check Token Permissions
Ensure GitHub token has `packages:write` scope:
```bash
gh auth status
# Should show authenticated with packages scope
```

## Enhanced Error Analysis

The script now provides specific error type identification:

- **404**: Version not found (may have been deleted already)
- **403**: Permission denied (token lacks `packages:write`)  
- **401**: Unauthorized (authentication issue)
- **422**: Unprocessable entity (invalid request format)
- **5xx**: Server errors (GitHub API temporarily unavailable)

## Expected Output Format

With enhanced logging, you should now see:
```
🔍 Attempting to delete Docker version ID: 490951546
🔍 DELETE endpoint: /users/hitoshura25/packages/container/webauthn-server/versions/490951546
🔍 Auth status: ✓ Logged in to github.com as hitoshura25 (oauth_token)
🔍 Executing: gh api --method DELETE /users/hitoshura25/packages/container/webauthn-server/versions/490951546
❌ Failed to delete Docker version: 490951546
❌ Exit code: 1
❌ Full error response: [detailed error message]
❌ Error type: [specific analysis]
⚠️ Continuing with remaining versions despite this failure
```

## Next Steps

1. **Run the quick test script** to get immediate feedback on the deletion failure
2. **Check the detailed error response** to identify the root cause
3. **Verify token permissions** if you see 403 errors
4. **Use the enhanced main script** which will now continue processing other versions even if one deletion fails

## Script Improvements Made

- ✅ Enhanced error capture in all deletion loops
- ✅ Added authentication validation and testing
- ✅ Created manual testing mode for isolated debugging  
- ✅ Added quick test script for rapid validation
- ✅ Improved error analysis with specific HTTP status handling
- ✅ Added continue-on-error logic to prevent script termination
- ✅ Enhanced trap handling for better error context

The script should now provide comprehensive debugging information to identify exactly why the deletion is failing.