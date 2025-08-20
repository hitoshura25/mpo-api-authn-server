# Maven Central Publishing Analysis & Recommendations (2025)

## Executive Summary

This document analyzes the current Maven Central Android publishing configuration and provides actionable recommendations for improved reliability and verification in 2025.

## Current Configuration Analysis

### ✅ Current Strengths
- **Bridge API Usage**: Using Portal OSSRH Staging API (`https://ossrh-staging-api.central.sonatype.com/service/local/staging/deploy/maven2/`)
- **Proper Authentication**: Central Portal user tokens correctly configured
- **GPG Signing**: Properly configured for production publishing
- **Conditional Publishing**: Safe staging/production environment separation
- **Centralized Configuration**: YAML-based configuration management
- **Enhanced Logging**: Added detailed diagnostic logging

### ⚠️ Areas for Improvement
- **Legacy Bridge API**: Currently using bridge API instead of modern Portal API
- **Manual Release Process**: No automated promotion from staging to live
- **Limited Verification**: Minimal post-publishing verification
- **No Modern Plugin Usage**: Not using `central-publishing-maven-plugin`

## 2025 Maven Central Landscape

### Key Changes in 2025
1. **OSSRH Sunset**: Legacy OSSRH shut down June 30, 2025
2. **Migration Complete**: All OSSRH namespaces migrated to Central Publisher Portal
3. **Bridge API**: Current "Portal OSSRH Staging API" is migration bridge
4. **Modern Recommendation**: Direct Portal Publisher API with official plugin

### Current vs Modern Approaches

| Aspect | Current (Bridge API) | Modern (Portal API) |
|--------|---------------------|-------------------|
| **URL** | `https://ossrh-staging-api.central.sonatype.com/...` | `https://central.sonatype.com/api/v1/publisher/...` |
| **Plugin** | Standard maven-publish | `central-publishing-maven-plugin` |
| **Deployment** | Manual staging + release | Automatic or user-managed |
| **Verification** | Manual portal checks | API-based status checks |
| **Modern Features** | Limited | Full Portal API features |

## Immediate Improvements Implemented

### 1. Enhanced Diagnostic Logging
**Added to `publish-android.yml`:**
- Detailed credential logging (without exposing secrets)
- API type identification
- Repository configuration visibility
- Step-by-step publishing process tracking

**Added to `build.gradle.kts.template`:**
- Repository configuration logging
- GPG signing status verification
- Credential source tracking
- API type detection

### 2. Post-Publishing Verification
**For Maven Central (Production):**
- Publication process timeline explanation
- Verification link generation
- Next steps guidance
- Manual release process documentation

**For GitHub Packages (Staging):**
- Real-time API verification
- Package availability confirmation
- Propagation delay handling
- Graceful failure management

### 3. Error Prevention
- Enhanced credential validation
- Missing signing key detection
- Repository URL validation
- Clear error messages with resolution steps

## Actionable Recommendations

### **Phase 1: Immediate (Current Setup) ✅ IMPLEMENTED**
- [x] Enhanced diagnostic logging
- [x] Post-publishing verification
- [x] Better error handling
- [x] Verification documentation

### **Phase 2: Short-term (1-2 weeks)**
1. **Add Central Portal API Status Checks**
   ```bash
   # Check deployment status via Portal API
   curl -H "Authorization: Bearer $TOKEN" \
        "https://central.sonatype.com/api/v1/publisher/deployments"
   ```

2. **Create Publishing Dashboard Script**
   - Automated status checking
   - Publishing history tracking
   - Deployment verification reporting

3. **Add Maven Central Search Verification**
   ```bash
   # Verify public availability
   curl "https://search.maven.org/solrsearch/select?q=g:io.github.hitoshura25+AND+a:mpo-webauthn-android-client"
   ```

### **Phase 3: Medium-term (1-2 months)**
1. **Migrate to Modern Portal API**
   - Replace bridge API with direct Portal API
   - Implement `central-publishing-maven-plugin`
   - Enable automatic deployment mode

2. **Implement JReleaser Integration**
   - Automated release management
   - Multi-platform publishing orchestration
   - Enhanced release notes generation

3. **Add Comprehensive Testing**
   - Test publishing to staging portal
   - Verify artifact signatures
   - Validate metadata completeness

### **Phase 4: Long-term (3-6 months)**
1. **Full Portal API Migration**
2. **Automated Release Pipeline**
3. **Multi-registry Publishing Strategy**
4. **Advanced Analytics and Monitoring**

## Current Publishing Flow Analysis

### Staging Flow (GitHub Packages) ✅ Working
```
1. Generate client → 2. Publish to GitHub Packages → 3. Verify via API → 4. Success
```

### Production Flow (Maven Central) ⚠️ Manual Steps Required
```
1. Generate client → 2. Publish to Portal OSSRH API → 3. Manual Portal verification → 4. Manual release → 5. Public availability (2-4 hours)
```

## Verification Status

### ✅ Implemented Improvements
- **Enhanced Logging**: Comprehensive diagnostic information
- **GitHub Packages Verification**: Real-time API verification
- **Maven Central Guidance**: Step-by-step verification instructions
- **Error Prevention**: Improved validation and error messages

### 🔍 Verification Steps
1. **GitHub Packages**: Automated API check with 10-second delay
2. **Maven Central**: Manual verification guidance with direct links
3. **Error Handling**: Graceful degradation for API delays

## Recommended Next Actions

### **Immediate (This Week)**
1. Test the enhanced logging in next publishing workflow
2. Verify the new verification steps work correctly
3. Document any issues found during testing

### **Short-term (Next 2 Weeks)**
1. Implement Central Portal API status checking
2. Create publishing status dashboard
3. Add Maven Central search API verification

### **Medium-term (Next 1-2 Months)**
1. Research `central-publishing-maven-plugin` migration path
2. Plan Portal API migration strategy
3. Implement automated release workflow

## Risk Assessment

### **Current Setup Risks**
- **Bridge API Deprecation**: May eventually be deprecated in favor of Portal API
- **Manual Release Process**: Human error in release process
- **Limited Automation**: Manual verification steps

### **Mitigation Strategies**
- **Enhanced Monitoring**: Implemented detailed logging and verification
- **Documentation**: Clear process documentation for manual steps
- **Planning**: Migration roadmap to modern APIs

## Conclusion

The current Maven Central publishing setup is **functionally correct** and uses appropriate 2025-compatible APIs. The implemented improvements provide:

1. **Better Visibility**: Enhanced logging shows exactly what's happening
2. **Reliable Verification**: Automated checks for GitHub Packages, guided verification for Maven Central
3. **Error Prevention**: Better validation prevents common publishing failures
4. **Future-Ready**: Architecture supports migration to modern Portal API

The setup successfully uses the Portal OSSRH Staging API (bridge) which is the correct modern approach for 2025, with a clear migration path to the direct Portal API when ready.

## Files Modified
- `.github/workflows/publish-android.yml` - Enhanced logging and verification
- `android-client-library/build.gradle.kts.template` - Diagnostic logging and validation
- `docs/setup/maven-central-publishing-analysis-2025.md` - This analysis document