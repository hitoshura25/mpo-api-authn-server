# JWT Key Rotation E2E Test Failures - Root Cause & Fix Plan

**Date**: 2025-10-27
**Status**: ✅ Completed
**Test Results**: ✅ 40/40 passing (100% success rate)

## Executive Summary

The JWT key rotation E2E tests were failing due to a **JWKS caching mismatch** between Envoy Gateway's cache duration (5 minutes) and the accelerated rotation settings (30-second intervals). This caused Envoy to use stale JWKS data, leading to incorrect JWT verification results.

**Resolution**: Implemented dynamic JWKS cache duration with smart defaults (10s for testing, 300s for production) and fixed Phase 3 test timing to account for cleanup occurring during the next rotation cycle.

## Test Failure Analysis (Original Issues - Now Resolved)

### Original Test Results (36/40 passing - BEFORE FIX)

**Passing Tests:**
- ✅ Phase 1: Initial key authentication (2/2 passing)
- ✅ Phase 2: After rotation - new key used, old key still valid (2/2 passing)
- ✅ All PyJWKClient compatibility tests (2/2 passing)
- ✅ All standard WebAuthn tests (8/8 passing)
- ✅ All JWT verification tests (8/8 passing)

**Failing Tests (NOW FIXED):**
- ~~❌ Phase 3 [chromium]: After retention period expires - K1 should be rejected~~ ✅ FIXED
- ~~❌ Phase 3 [Mobile Chrome]: After retention period expires - K1 should be rejected~~ ✅ FIXED
- ~~❌ Phase 4 [chromium]: Multiple rotations - K3 should be valid~~ ✅ FIXED
- ~~❌ Phase 4 [Mobile Chrome]: Multiple rotations - K3 should be valid~~ ✅ FIXED

### Failure Details

#### Phase 3 Failure (Line 190 in jwt-key-rotation.spec.js)
```javascript
// After waiting 35s for retention to expire
const responseWithK1 = await request.get('http://localhost:8000/api/user/profile', {
  headers: { 'Authorization': `Bearer ${jwtK1}` }
});

expect(responseWithK1.ok()).toBe(false);  // FAILS: Expected false, received true
expect(responseWithK1.status()).toBe(401); // K1 should be rejected
```

**What's happening:**
1. K1 is created and retired at T=0
2. After 30s retention, K1 is **deleted from database** (Phase 4 cleanup)
3. Server's JWKS endpoint no longer returns K1
4. Test waits 35s and verifies K1 should be rejected
5. **But Envoy's cached JWKS (300s TTL) still includes K1**
6. Envoy accepts K1 token using stale cache ❌

#### Phase 4 Failure (Line 239 in jwt-key-rotation.spec.js)
```javascript
// After K2 → K3 rotation
const responseWithK3 = await request.get('http://localhost:8000/api/user/profile', {
  headers: { 'Authorization': `Bearer ${jwtK3}` }
});

expect(responseWithK3.ok()).toBe(true);  // FAILS: Expected true, received false
expect(responseWithK3.status()).toBe(200);
```

**What's happening:**
1. K3 becomes active after second rotation
2. Server's JWKS endpoint **immediately includes K3**
3. Test verifies K3 token should be valid
4. **But Envoy's cached JWKS doesn't have K3 yet**
5. Envoy rejects K3 token using stale cache ❌

## Root Cause: JWKS Cache Duration Mismatch

### Current Configuration

**MCP Template Configuration:**
- File: `mcp-server-webauthn-client/src/templates/vanilla/docker/envoy-gateway.yaml.hbs`
- Line 82: `seconds: 300  # Cache JWKS for 5 minutes`
- **This is hardcoded** - no configuration parameter exists

**Test Client Configuration:**
- Key rotation interval: **30 seconds**
- Grace period: **15 seconds** (0.25 minutes)
- Retention period: **30 seconds** (0.5 minutes)
- Full rotation cycle: **45 seconds** (30s interval + 15s grace)

**The Problem:**
```
Envoy JWKS cache: 300 seconds (5 minutes)
Key rotation cycle: 45 seconds
Retention period: 30 seconds

Timeline:
T=0s:    K1 active, K2 pending
T=15s:   K2 active, K1 retired
T=45s:   K1 retention expires, K1 deleted from JWKS
         Envoy still caching JWKS from T=0s (has K1 for 300s!)
T=300s:  Envoy cache expires, fetches fresh JWKS (finally removes K1)
```

### Evidence from Server Logs

```
2025-10-27 15:44:21.885 INFO KeyRotationService - Phase 4: Cleaning up expired key: webauthn-2025-10-27-153532 (expired at 2025-10-27T15:44:06.770944Z)
2025-10-27 15:44:51.905 INFO KeyRotationService - Key rotation needed. Key age: PT30.029986386S, Threshold: PT30S
2025-10-27 15:45:07.087 INFO KeyRotationService - Phase 4: Cleaning up expired key: webauthn-2025-10-27-153617 (expired at 2025-10-27T15:44:51.875413Z)
```

**Server is working correctly:**
- Rotates keys every ~30 seconds ✅
- Cleans up expired keys after retention period ✅
- JWKS endpoint returns current keys only ✅

**Verification (Direct JWKS Query):**
```bash
$ curl -s http://localhost:8000/.well-known/jwks.json | jq '.keys[].kid'
"webauthn-2025-10-27-154837"  # Current active key
"webauthn-2025-10-27-154752"  # Recently retired key (within retention)
# No older keys - correctly cleaned up!
```

**But Envoy Gateway uses cached version** - doesn't see real-time changes for up to 5 minutes.

## Solution: Dynamic JWKS Cache Duration

### Strategy

Add a **configurable JWKS cache duration** to the MCP template generator with intelligent defaults:

- **Production mode**: 300 seconds (5 minutes) - Standard for production systems
- **Testing mode**: 10 seconds - Allows rapid rotation testing without stale cache issues

**Detection Logic:**
```typescript
// If rotation interval is very short (< 60s), assume testing mode
if (jwt_rotation_interval_seconds && parseInt(jwt_rotation_interval_seconds) < 60) {
  jwks_cache_duration = 10; // Testing mode
} else {
  jwks_cache_duration = 300; // Production mode
}
```

### Implementation Plan

#### Step 1: Update MCP Generator Interface

**File**: `mcp-server-webauthn-client/src/lib/generator.ts`

**Changes Required:**

1. Add parameter to `GenerateWebClientArgs` interface (around line 45):
```typescript
interface GenerateWebClientArgs {
  // ... existing parameters

  // JWT key rotation configuration (optional - for testing)
  jwt_rotation_enabled?: string;
  jwt_rotation_interval_seconds?: string;
  jwt_grace_period_minutes?: string;
  jwt_retention_minutes?: string;

  // NEW: JWKS cache duration for Envoy Gateway
  jwks_cache_duration_seconds?: number;
}
```

2. Add smart default calculation in function body (around line 75-85):
```typescript
export async function generateWebClient(args: GenerateWebClientArgs) {
  const {
    // ... existing destructuring
    jwt_rotation_enabled,
    jwt_rotation_interval_seconds,
    jwt_grace_period_minutes,
    jwt_retention_minutes,
    jwks_cache_duration_seconds
  } = args;

  // ... existing validation code

  // Calculate smart JWKS cache duration
  let calculated_jwks_cache_duration = jwks_cache_duration_seconds;

  if (!calculated_jwks_cache_duration) {
    // Auto-detect based on rotation interval
    if (jwt_rotation_interval_seconds && parseInt(jwt_rotation_interval_seconds) < 60) {
      calculated_jwks_cache_duration = 10; // Testing mode: short cache
    } else {
      calculated_jwks_cache_duration = 300; // Production mode: 5 minutes
    }
  }
```

3. Add to template_vars (around line 186):
```typescript
const template_vars = {
  server_url,
  client_port: forward_port,
  server_port,
  relying_party_id,
  relying_party_name,
  // Infrastructure ports
  postgres_host_port,
  redis_host_port,
  gateway_host_port,
  gateway_admin_port,
  // Jaeger ports
  jaeger_ui_port,
  jaeger_collector_http_port,
  jaeger_collector_grpc_port,
  jaeger_otlp_grpc_port,
  jaeger_otlp_http_port,
  jaeger_agent_compact_port,
  jaeger_agent_binary_port,
  jaeger_agent_config_port,
  // JWT rotation parameters (optional)
  jwt_rotation_enabled,
  jwt_rotation_interval_seconds,
  jwt_grace_period_minutes,
  jwt_retention_minutes,
  // NEW: JWKS cache duration
  jwks_cache_duration_seconds: calculated_jwks_cache_duration
};
```

#### Step 2: Update Envoy Gateway Template

**File**: `mcp-server-webauthn-client/src/templates/vanilla/docker/envoy-gateway.yaml.hbs`

**Change at line 81-82:**

```yaml
# BEFORE (hardcoded):
                            cache_duration:
                              seconds: 300  # Cache JWKS for 5 minutes

# AFTER (dynamic with smart default):
                            cache_duration:
                              seconds: {{#if jwks_cache_duration_seconds}}{{jwks_cache_duration_seconds}}{{else}}300{{/if}}  # JWKS cache duration (auto-adjusted for testing)
```

**Add comment explaining the behavior:**
```yaml
                          remote_jwks:
                            http_uri:
                              uri: http://webauthn-server:8080/.well-known/jwks.json
                              cluster: webauthn_server
                              timeout: 5s
                            # Cache duration: Auto-adjusted based on rotation interval
                            # - Testing mode (rotation < 60s): 10 seconds cache
                            # - Production mode: 300 seconds (5 minutes) cache
                            cache_duration:
                              seconds: {{#if jwks_cache_duration_seconds}}{{jwks_cache_duration_seconds}}{{else}}300{{/if}}
```

#### Step 3: Update Test Client Generator Script

**File**: `generate-rotation-test-client.mjs`

**Update config object** (around line 10-20):

```javascript
const config = {
  project_path: join(__dirname, 'test-key-rotation-client'),
  framework: 'vanilla',

  // Accelerated rotation for testing
  jwt_rotation_enabled: 'true',
  jwt_rotation_interval_seconds: '30',  // 30 second rotation
  jwt_grace_period_minutes: '0.25',     // 15 seconds grace
  jwt_retention_minutes: '0.5',          // 30 seconds retention

  // NEW: Short JWKS cache for testing
  jwks_cache_duration_seconds: 10       // 10 second cache (allows rapid rotation testing)
};
```

**Rationale:**
- With 10s cache and 30s rotation, Envoy will see fresh JWKS at most 10s stale
- This allows Phase 3 to correctly reject expired keys (after 35s wait, cache refreshes 3-4 times)
- This allows Phase 4 to correctly accept new keys (K3 appears in JWKS within 10s)

#### Step 4: Update Template README Documentation

**File**: `mcp-server-webauthn-client/src/templates/vanilla/README.md.hbs`

**Add section explaining JWKS caching:**

```markdown
### JWKS Cache Duration

The Envoy Gateway caches JWKS (JSON Web Key Set) responses to optimize performance. The cache duration is automatically adjusted based on your JWT rotation configuration:

**Automatic Configuration:**
- **Testing Mode** (rotation interval < 60s): 10 second cache
  - Allows rapid key rotation testing
  - Envoy sees fresh keys quickly during accelerated rotation

- **Production Mode** (rotation interval ≥ 60s): 300 second (5 minute) cache
  - Standard production configuration
  - Reduces load on JWKS endpoint
  - Aligns with industry best practices

**Manual Override:**
You can explicitly set the cache duration when generating the client:

```javascript
await generateWebClient({
  project_path: './my-client',
  jwt_rotation_interval_seconds: '30',
  jwks_cache_duration_seconds: 15  // Custom cache duration
});
```

**Important:** If using very short rotation intervals (< 60s) for testing, ensure the JWKS cache duration is proportionally short to avoid stale cache issues.
```

### Step 5: Rebuild and Test

**Commands:**
```bash
# 1. Rebuild MCP templates
cd /Users/vinayakmenon/mpo-api-authn-server-key_rotation/mcp-server-webauthn-client
npm run build

# 2. Regenerate test client with new configuration
cd /Users/vinayakmenon/mpo-api-authn-server-key_rotation
rm -rf test-key-rotation-client
node generate-rotation-test-client.mjs

# 3. Update docker-compose to use test image
sed -i '' 's/image: hitoshura25\/webauthn-server:latest/image: webauthn-server:test-key-rotation\n    pull_policy: never/' test-key-rotation-client/docker/docker-compose.yml

# 4. Restart Docker stack with clean volumes
cd test-key-rotation-client/docker
docker compose down -v
docker compose up -d

# 5. Wait for services to be healthy
sleep 10

# 6. Install dependencies and run tests
cd ..
npm install
npm run build
npm test
```

**Expected Result:**
```
40 passed (all tests passing!)
```

## Verification Steps

After implementing the fix, verify:

1. **Envoy Configuration Check:**
```bash
# Check generated Envoy config has correct cache duration
grep -A 2 "cache_duration" test-key-rotation-client/docker/envoy-gateway.yaml
# Should show: seconds: 10
```

2. **Phase 3 Behavior:**
```
T=0s:    K1 active
T=30s:   K2 active, K1 retired
T=65s:   K1 deleted from JWKS
         Envoy cache (10s) has refreshed 6-7 times
         Envoy sees K1 is gone → K1 tokens rejected ✅
```

3. **Phase 4 Behavior:**
```
T=0s:    K1 active
T=30s:   K2 active (first rotation)
T=60s:   K3 active (second rotation)
         K3 immediately in JWKS
         Envoy cache refreshes within 10s
         Envoy sees K3 → K3 tokens accepted ✅
```

## Benefits of This Approach

1. **Backward Compatible**: Existing production configs with long rotation intervals (180 days default) continue using 5-minute cache
2. **Testing-Friendly**: Accelerated testing automatically uses short cache without manual configuration
3. **Configurable**: Explicit override available for custom scenarios
4. **Self-Documenting**: Template generation logs show which mode is selected
5. **Industry Standard**: 5-minute JWKS cache aligns with OAuth2/OIDC best practices for production

## Alternative Solutions Considered

### Alternative 1: Increase Rotation Interval
**Rejected**: Would make tests much slower (need hours to test full rotation lifecycle)

### Alternative 2: Disable Envoy JWKS Caching
**Rejected**: Not realistic for production scenarios, defeats the purpose of testing production-like configuration

### Alternative 3: Use Time Mocking
**Rejected**: Doesn't test real-world timing behavior, can hide race conditions

### Alternative 4: Separate Test and Production Templates
**Rejected**: Code duplication, maintenance burden, divergence between test and production configs

**Selected Solution** (Dynamic Cache Duration) is the best balance of:
- Realistic production behavior
- Fast test execution
- Minimal code duplication
- Clear configuration intent

## References

- **Envoy JWT Authentication**: https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/http/jwt_authn/v3/config.proto
- **JWKS RFC 7517**: https://datatracker.ietf.org/doc/html/rfc7517
- **OAuth2 Best Practices**: https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics
- **Test Results**: `/Users/vinayakmenon/mpo-api-authn-server-key_rotation/test-key-rotation-client/playwright-report/`

## Implementation Results

### Final Test Results: ✅ 40/40 PASSING (100%)

**Before Fix**: 36/40 passing (4 failures in Phase 3 and Phase 4)
**After Fix**: 40/40 passing (0 failures)

### Changes Implemented

1. ✅ **generator.ts** - Added `jwks_cache_duration_seconds` parameter with smart defaults
   - Testing mode (rotation < 60s): 10-second cache
   - Production mode: 300-second cache (5 minutes)

2. ✅ **envoy-gateway.yaml.hbs** - Dynamic JWKS cache duration using Handlebars variable

3. ✅ **generate-rotation-test-client.mjs** - Explicit 10-second cache for testing

4. ✅ **jwt-key-rotation.spec.js.hbs** - Fixed Phase 3 wait time
   - **Critical Discovery**: Keys are only deleted during next rotation's Phase 4 cleanup
   - Changed wait from 35s to 60s to account for:
     - 30s retention period
     - Next rotation cycle (45s = 30s interval + 15s grace)
     - Envoy cache refresh (10s)

### Test Execution Summary

```
🎯 Final Results: 40 passed (1.4m)

✅ Phase 1: Initial key authentication (2/2)
✅ Phase 2: After rotation - old key still valid (2/2)
✅ Phase 3: After retention - old key rejected (2/2) ← FIXED!
✅ Phase 4: Multiple rotations working (2/2) ← FIXED!
✅ PyJWKClient compatibility tests (2/2)
✅ Standard WebAuthn tests (8/8)
✅ JWT verification tests (8/8)
✅ Protected endpoint access tests (14/14)
```

### Key Insights Discovered

1. **JWKS Cache Mismatch**: Envoy's 5-minute cache was incompatible with 30-second rotation testing
2. **Cleanup Timing**: Keys are NOT deleted immediately when retention expires - cleanup only occurs during the NEXT rotation's Phase 4
3. **Smart Defaults**: Auto-detection based on rotation interval provides best of both worlds (fast testing + production-ready defaults)
