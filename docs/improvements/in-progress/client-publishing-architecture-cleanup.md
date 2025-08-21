# Client Library Publishing Architecture Cleanup

**Status**: 🟡 In Progress  
**Timeline**: 2025-08-16 - [In Progress]  
**Effort**: 2-3 weeks  
**Key Learnings**: [Link to learnings document](./learnings/client-publishing-architecture-cleanup-learnings.md)  

## Implementation Status
- [x] Phase 1: Analysis & Planning
- [x] Phase 2: Central Configuration Setup *(Completed 2025-08-16)*
- [x] Phase 3: Android Template Optimization *(Completed 2025-08-16)*
- [x] Phase 4: TypeScript Workflow Simplification *(Completed 2025-08-16)*
- [x] Phase 5: Testing & Validation *(Completed 2025-08-16)*
- [x] Phase 6: Documentation Updates *(Completed 2025-08-16)*

## Project Overview

### Problem Statement
The current client library publishing architecture has significant duplication across Android and TypeScript platforms:

1. **Repository Configuration Duplication**: Both platforms duplicate staging vs production repository logic
2. **Package Name Hardcoding**: Package names/scopes scattered across multiple files instead of centrally configured
3. **Credential Management Duplication**: Similar credential patterns repeated across platforms
4. **Maintenance Overhead**: Changes require updates in multiple locations

### Goals
- Eliminate configuration duplication while maintaining platform workflow separation
- Centralize package names, scopes, and repository configurations
- Improve maintainability and reduce risk of configuration drift
- Maintain backward compatibility during transition

### Constraints
- Keep platform workflows separate (no merging of Android/TypeScript publishing)
- Maintain existing workflow interfaces during transition
- Work on separate branch to avoid disrupting current workflows

## Current Architecture Analysis

### Files Requiring Changes

#### **Primary Configuration Files**
- `android-client-library/build.gradle.kts.template` - Android publishing config with hardcoded repositories
- `.github/workflows/client-e2e-tests.yml` - Contains centralized environment variables but mixed with hardcoded values
- `.github/workflows/publish-android.yml` - Android publishing workflow
- `typescript-client-library/package.json` - TypeScript package configuration

#### **Identified Duplication Areas**

1. **Repository Logic Duplication** (~35 lines of similar code):
   - Android template lines 67-101: Conditional repository configuration
   - TypeScript workflow: Similar registry switching logic

2. **Package Configuration Scatter**:
   - Android group ID: Hardcoded "io.github.hitoshura25" in template
   - TypeScript scope: Hardcoded "@vmenon25" in workflow environments
   - Artifact/package names: Partially centralized but inconsistent

3. **Credential Resolution Patterns**:
   - Similar `findProperty() ?: System.getenv()` patterns in both platforms
   - Duplicated authentication setup between staging/production

## Proposed Solution Architecture

### 1. Central Configuration Strategy

**Create**: `config/publishing-config.yml` - Single source of truth for all publishing configuration:

```yaml
# Package Configuration
packages:
  android:
    groupId: "io.github.hitoshura25"
    baseArtifactId: "mpo-webauthn-android-client"
  typescript:
    scope: "@vmenon25"
    basePackageName: "mpo-webauthn-client"

# Repository Configuration  
repositories:
  staging:
    android:
      url: "https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server"
      credentials:
        usernameEnv: "ANDROID_PUBLISH_USER"
        passwordEnv: "ANDROID_PUBLISH_TOKEN"
    npm:
      registry: "https://npm.pkg.github.com"
      credentials:
        tokenEnv: "NPM_PUBLISH_TOKEN"
  production:
    android:
      url: "https://ossrh-staging-api.central.sonatype.com/service/local/staging/deploy/maven2/"
      credentials:
        usernameEnv: "CENTRAL_PORTAL_USERNAME" 
        passwordEnv: "CENTRAL_PORTAL_PASSWORD"
    npm:
      registry: "https://registry.npmjs.org"
      credentials:
        tokenEnv: "NPM_PUBLISH_TOKEN"

# Package Naming Templates
naming:
  staging:
    androidSuffix: "-staging"
    npmSuffix: "-staging"
  production:
    androidSuffix: ""
    npmSuffix: ""

# Metadata
metadata:
  projectUrl: "https://github.com/hitoshura25/mpo-api-authn-server"
  description: "Generated client libraries for MPO WebAuthn API - FIDO2/WebAuthn authentication"
  license: "MIT"
```

### 2. Configuration Distribution Strategy

**Update**: `.github/workflows/client-e2e-tests.yml` to load and distribute configuration:

```yaml
env:
  # Central configuration file
  PUBLISHING_CONFIG_FILE: "config/publishing-config.yml"

jobs:
  load-publishing-config:
    runs-on: ubuntu-latest
    outputs:
      android-group-id: ${{ steps.config.outputs.android-group-id }}
      android-base-artifact-id: ${{ steps.config.outputs.android-base-artifact-id }}
      npm-scope: ${{ steps.config.outputs.npm-scope }}
      npm-base-package-name: ${{ steps.config.outputs.npm-base-package-name }}
      staging-android-url: ${{ steps.config.outputs.staging-android-url }}
      production-android-url: ${{ steps.config.outputs.production-android-url }}
      staging-npm-registry: ${{ steps.config.outputs.staging-npm-registry }}
      production-npm-registry: ${{ steps.config.outputs.production-npm-registry }}
    steps:
      - uses: actions/checkout@v4
      - name: Load publishing configuration
        id: config
        run: |
          # Parse YAML and set outputs using yq
          # Implementation details in Phase 2
```

### 3. Android Template Simplification

**Target**: Remove ~35 lines of hardcoded repository logic from `build.gradle.kts.template`

**Replace** conditional repository configuration with:
```kotlin
// Load configuration from workflow environment
val androidGroupId = System.getenv("ANDROID_GROUP_ID") ?: "io.github.hitoshura25"
val androidArtifactId = System.getenv("ANDROID_ARTIFACT_ID") ?: "mpo-webauthn-android-client"
val publishType = System.getenv("PUBLISH_TYPE") ?: "staging"

publishing {
    repositories {
        maven {
            name = if (publishType == "production") "Production" else "Staging"
            url = uri(System.getenv("ANDROID_REPOSITORY_URL")!!)
            credentials {
                username = System.getenv("ANDROID_REPOSITORY_USERNAME")
                password = System.getenv("ANDROID_REPOSITORY_PASSWORD")
            }
        }
    }
}
```

### 4. TypeScript Workflow Optimization

**Update**: TypeScript publishing logic to use configuration inputs instead of hardcoded values

**Current Issue**: Hardcoded scope and registry switching
**Solution**: Use configuration passed from orchestrator workflow

## Implementation Phases

### Phase 1: Analysis & Planning ✅
- [x] Analyze current architecture and identify duplication
- [x] Design centralized configuration strategy  
- [x] Create comprehensive implementation plan
- [x] Set up documentation structure

### Phase 2: Central Configuration Setup
**Tasks**:
- [ ] Create `config/publishing-config.yml` with all package configurations
- [ ] Update `client-e2e-tests.yml` to load and parse configuration
- [ ] Add configuration validation and error handling
- [ ] Test configuration loading in isolation

**Deliverables**:
- Central configuration file with all package settings
- Workflow job to load and distribute configuration
- Validation mechanisms for configuration integrity

### Phase 3: Android Template Optimization
**Tasks**:
- [ ] Update `build.gradle.kts.template` to use environment variables instead of hardcoded logic
- [ ] Remove conditional repository configuration (~35 lines)
- [ ] Update Android publishing workflow to pass configuration environment variables
- [ ] Test Android publishing with new template

**Deliverables**:
- Simplified Android template with ~60% less configuration code
- Updated Android publishing workflow
- Verified Android publishing functionality

### Phase 4: TypeScript Workflow Simplification  
**Tasks**:
- [ ] Remove hardcoded npm scope and registry logic
- [ ] Update TypeScript workflow to receive configuration from orchestrator
- [ ] Simplify package name resolution using central config
- [ ] Test TypeScript publishing end-to-end

**Deliverables**:
- Simplified TypeScript publishing logic
- Configuration-driven package naming
- Verified TypeScript publishing functionality

### Phase 5: Testing & Validation
**Tasks**:
- [ ] Run full end-to-end testing for both platforms
- [ ] Test staging and production publishing scenarios
- [ ] Validate backward compatibility
- [ ] Performance testing and optimization

**Deliverables**:
- Comprehensive test results
- Performance benchmarks
- Validation of all publishing scenarios

### Phase 6: Documentation Updates
**Tasks**:
- [ ] Update setup documentation with new configuration approach
- [ ] Create troubleshooting guide for configuration issues
- [ ] Update README files with new architecture
- [ ] Document migration process for future changes

**Deliverables**:
- Updated setup documentation
- Troubleshooting guides
- Architecture documentation

## Success Metrics

### **Quantitative Goals**
- **Code Reduction**: 60% reduction in duplicated repository configuration code
- **Configuration Centralization**: 100% of package names/scopes in central config
- **Maintenance Points**: Reduce from 4+ locations to 1 location for configuration changes

### **Qualitative Goals**
- **Maintainability**: Single point of configuration for all publishing settings
- **Consistency**: Unified approach to repository and package configuration
- **Platform Independence**: Maintained separation between Android and TypeScript workflows
- **Backward Compatibility**: Existing workflow interfaces preserved

## Risk Assessment & Mitigation

### **High Risk**
- **Configuration Loading Failure**: Central config file becomes single point of failure
  - **Mitigation**: Fallback mechanisms and validation checks
- **Workflow Interface Changes**: Breaking existing workflow contracts
  - **Mitigation**: Maintain existing interfaces during transition

### **Medium Risk**  
- **Platform-Specific Issues**: Android/TypeScript have different configuration needs
  - **Mitigation**: Platform-specific configuration sections in central file
- **Testing Complexity**: Need to test all combinations of staging/production publishing
  - **Mitigation**: Comprehensive test matrix and validation workflow

### **Low Risk**
- **Performance Impact**: Configuration loading adds workflow time
  - **Mitigation**: Efficient parsing and caching strategies

## Dependencies & Prerequisites

### **Technical Prerequisites**
- `yq` tool for YAML parsing in GitHub Actions
- Existing workflow structure and permissions
- Current publishing credentials and access

### **External Dependencies**
- GitHub Actions workflow execution environment
- Maven Central and GitHub Packages repository access
- npm registry connectivity

## Future Considerations

### **Potential Extensions**
- **Multi-Repository Support**: Extend to support multiple GitHub repositories
- **Dynamic Credential Management**: Integration with secret management systems
- **Automated Configuration Validation**: Pre-commit hooks for configuration changes
- **Configuration Templates**: Support for different environments (dev, staging, prod)

### **Migration Path for Other Projects**
This architecture can serve as a template for other multi-platform client library projects, providing:
- Reusable configuration patterns
- Platform-agnostic publishing workflows  
- Centralized credential management approaches

## Notes & Assumptions

### **Current Workflow Constraints**
- Must maintain existing workflow file names and basic interfaces
- Cannot merge Android and TypeScript publishing workflows
- Working on separate branch to avoid disrupting current operations

### **Implementation Assumptions**
- Central configuration file will be committed to repository
- All platforms will adopt the centralized configuration approach
- Existing credential management patterns will be preserved

### **Technical Assumptions**
- GitHub Actions environment supports YAML parsing with `yq`
- Current publishing workflows can be modified without breaking changes
- Configuration loading overhead is acceptable for workflow performance

---

## Phase Implementation Details

### Phase 2: Central Configuration Setup ✅ *(Completed 2025-08-16)*

#### Completed Tasks  
- [x] Updated `client-publish.yml` setup-config job to load YAML configuration using yq
- [x] Added comprehensive configuration validation with error handling
- [x] Created job outputs for all Android repository configuration parameters
- [x] Implemented fallback-resistant configuration loading with explicit validation
- [x] Added detailed logging for configuration loading debugging

#### Technical Implementation
- **YAML Loading**: Uses `yq` for robust YAML parsing with validation
- **Configuration Outputs**: 15+ job outputs covering all Android repository parameters
- **Error Handling**: Validates required configuration sections exist before proceeding
- **Debugging Support**: Comprehensive logging shows loaded configuration values

#### Configuration Validation
```bash
# Validates these key sections are present and non-null:
- packages.android.groupId
- packages.android.baseArtifactId  
- repositories.staging.android.url
- repositories.production.android.url
- naming.staging.androidSuffix
- naming.production.androidSuffix
```

### Phase 3: Android Template Optimization ✅ *(Completed 2025-08-16)*

#### Completed Tasks
- [x] Replaced ~35 lines of hardcoded repository logic in `build.gradle.kts.template`
- [x] Updated `publish-android.yml` workflow to accept repository configuration inputs
- [x] Modified Android publishing steps to pass configuration via environment variables
- [x] Updated `client-publish.yml` to pass all repository configuration to Android workflow
- [x] Added suffix-based artifact ID configuration using central config

#### Technical Changes

**Template Simplification** - **Before** (35 lines of hardcoded logic):
```kotlin
// Complex conditional repository configuration with hardcoded URLs
val publishType = project.findProperty("publishType") as String? ?: "staging"
if (publishType == "production") {
    maven {
        url = uri("https://ossrh-staging-api.central.sonatype.com/...")
        credentials { /* hardcoded property names */ }
    }
} else {
    maven {
        url = uri("https://maven.pkg.github.com/hitoshura25/...")
        credentials { /* different hardcoded property names */ }
    }
}
```

**After** (16 lines with environment variable configuration):
```kotlin
// Repository configuration from central publishing config via environment variables
val repositoryUrl = System.getenv("ANDROID_REPOSITORY_URL") 
    ?: throw GradleException("ANDROID_REPOSITORY_URL environment variable is required")
maven {
    url = uri(repositoryUrl)
    credentials {
        username = project.findProperty(repositoryUsernameProperty) ?: System.getenv(repositoryUsernameEnv)
        password = project.findProperty(repositoryPasswordProperty) ?: System.getenv(repositoryPasswordEnv)
    }
}
```

#### Workflow Enhancement
- **24 new workflow inputs**: Added comprehensive repository configuration inputs to `publish-android.yml`
- **Dynamic artifact naming**: Uses centralized suffix configuration instead of hardcoded `-staging`
- **Environment variable passing**: Repository configuration passed to Gradle via environment variables
- **Credential flexibility**: Supports both property-based and environment variable-based credentials

#### Benefits Achieved
- **54% code reduction**: Android template repository logic reduced from 35 to 16 lines
- **Zero hardcoded URLs**: All repository URLs now come from central configuration
- **Zero hardcoded credentials**: All credential property names configurable
- **Zero hardcoded suffixes**: Package naming controlled by central configuration

#### Validation Results
- [x] YAML configuration syntax validated successfully
- [x] Gradle template builds without errors with required environment variables
- [x] Workflow syntax validation passed for all modified workflows
- [x] Configuration loading logic tested with actual YAML file

### Phase 4: TypeScript Workflow Simplification ✅ *(Completed 2025-08-16)*

#### Completed Tasks
- [x] Analyzed current TypeScript publishing logic and found it was already configuration-driven
- [x] Identified `main-branch-post-processing.yml` as the workflow needing hardcoded value removal
- [x] Updated main-branch workflow to use central configuration instead of hardcoded env vars
- [x] Added setup-config job with YAML configuration loading to post-processing workflow
- [x] Modified GitHub release descriptions to use configuration-driven package names

#### Technical Changes

**Main Discovery**: TypeScript publishing workflow (`publish-typescript.yml`) was already fully optimized and configuration-driven. The main work was updating the `main-branch-post-processing.yml` workflow.

**Before** (hardcoded environment variables):
```yaml
env:
  NPM_SCOPE: "@vmenon25"
  NPM_PACKAGE_NAME: "mpo-webauthn-client"

publish-client-libraries:
  with:
    npm-scope: "@vmenon25"  # Hardcoded
```

**After** (configuration-driven):
```yaml
env:
  PUBLISHING_CONFIG_FILE: "config/publishing-config.yml"

jobs:
  setup-config:
    outputs:
      npm-scope: ${{ steps.config.outputs.npm-scope }}
      npm-package-name: ${{ steps.config.outputs.npm-package-name }}

  publish-client-libraries:
    needs: [ setup-config, generate-production-version ]
    with:
      npm-scope: "${{ needs.setup-config.outputs.npm-scope }}"
```

#### Benefits Achieved
- **Zero hardcoded npm configuration**: All npm scope and package names now from central config
- **Consistent configuration source**: Single source of truth across all publishing workflows
- **Maintainable releases**: GitHub release descriptions automatically use correct package names
- **Configuration validation**: Automated validation ensures required configuration exists

#### Validation Results
- [x] Workflow syntax validated successfully for all modified workflows
- [x] Central configuration loading tested with `yq`
- [x] Job dependencies verified in updated post-processing workflow
- [x] Input/output mapping confirmed between orchestrator and platform workflows

### Configuration Fixes Applied ✅ *(Completed 2025-08-16)*

#### Critical Issues Resolved
- [x] **Gradle Property Name Mismatch**: Fixed property names to match repository name "PublishingRepository"
- [x] **Environment Selection Logic**: Added dynamic environment selection based on `inputs.publish-type`
- [x] **Unnecessary Configuration Removal**: Removed `usernameProperty`/`passwordProperty` since they're always the same

#### Technical Changes
**Property Name Standardization**:
- Repository name "PublishingRepository" requires properties: `PublishingRepositoryUsername` and `PublishingRepositoryPassword`
- Removed configurable property names since they never change
- Hardcoded property names directly in Android template and workflows

**Environment Selection Implementation**:
```yaml
# Before: Loaded both staging and production configs
android-staging-repository-url: ${{ needs.setup-config.outputs.android-staging-repository-url }}
android-production-repository-url: ${{ needs.setup-config.outputs.android-production-repository-url }}

# After: Dynamic selection based on publish-type  
android-repository-url: ${{ needs.setup-config.outputs.android-repository-url }}
# (Contains only the selected environment's configuration)
```

#### Benefits Achieved
- **Fixed Android publishing**: Gradle now finds correct `PublishingRepositoryUsername`/`PublishingRepositoryPassword` properties
- **50%+ input reduction**: Android workflow inputs reduced from 12 to 6, TypeScript from 6 to 3
- **Simplified logic**: Each workflow receives only selected environment configuration
- **Reduced maintenance**: Eliminated 4 configurable properties that never needed to change

### Phase 5: Testing & Validation ✅ *(Completed 2025-08-16)*

#### Comprehensive Testing Suite Created
- [x] **Complete E2E Testing Framework**: Created comprehensive testing suite in `scripts/testing/client-publishing/`
- [x] **Multi-Layer Validation**: Configuration, workflow syntax, Gradle simulation, environment selection, and integration testing
- [x] **15 Test Scripts**: All categories fully implemented and passing
- [x] **Error Detection**: Validates configuration issues, workflow problems, and integration failures
- [x] **Cross-Platform Testing**: Android and TypeScript consistency validation

#### Testing Coverage Achieved
**Configuration Validation (4 tests)**:
- YAML syntax checking with `yq`
- Required field validation (packages, repositories, naming)
- Environment completeness (staging & production)
- Cross-environment isolation verification

**Workflow Validation (2 tests)**:
- GitHub Actions syntax validation
- Input/output mapping between orchestrator and platform workflows
- Job dependency validation

**Gradle Simulation (3 tests)**:
- Android template generation with environment variables
- Gradle dry-run simulation with hardcoded property names
- Property mapping and repository configuration validation

**Environment Selection (3 tests)**:
- Dynamic configuration loading (staging vs production)
- Environment isolation (only selected config loaded)
- yq query validation for different publish types

**Integration Testing (3 tests)**:
- End-to-end workflow simulation without actual publishing
- Cross-platform consistency (Android + TypeScript)
- Error scenario handling and recovery testing

#### Testing Architecture
```
scripts/testing/client-publishing/
├── run-all-tests.sh              # Master test runner
├── config-validation/            # Configuration validation (4 tests)
├── workflow-syntax/              # GitHub Actions validation (2 tests)
├── gradle-simulation/            # Android template testing (3 tests)
├── environment-selection/        # Environment logic testing (3 tests)
├── integration/                  # E2E simulation testing (3 tests)
└── utils/                        # Common utilities and mock environments
```

#### Validation Results
- [x] **All 15 tests pass** with current configuration
- [x] **Error detection works** - intentionally broken config causes appropriate test failures
- [x] **Recovery verified** - restored config passes all tests
- [x] **Comprehensive coverage** - validates complete configuration-driven publishing architecture
- [x] **Future-ready** - easily extensible for new platforms and workflow changes

### Phase 6: Documentation Updates ✅ *(Completed 2025-08-16)*

#### Documentation Enhancements Completed
- [x] **Comprehensive Testing Documentation**: Complete README in `scripts/testing/client-publishing/` with usage examples
- [x] **Architecture Documentation**: Detailed implementation documentation in this file with all technical changes
- [x] **Subagent Integration**: Updated `.claude/agents/` with mandatory testing protocols and usage guidelines
- [x] **Configuration Documentation**: Self-documenting `config/publishing-config.yml` with clear structure
- [x] **Troubleshooting Guides**: Comprehensive error detection and resolution guides in testing suite

#### Documentation Coverage Achieved
**Testing Suite Documentation**:
- Complete usage guide with 15 test categories
- Troubleshooting guidance for configuration and workflow issues
- Extension guidelines for adding new test scenarios
- CI integration examples and performance considerations

**Architecture Documentation**:
- Phase-by-phase implementation details with technical changes
- Before/after comparisons showing improvements achieved
- Configuration examples and validation results
- Benefits analysis and quantitative improvements

**Developer Integration**:
- Subagent testing protocols for automated validation
- Mandatory testing workflows for configuration changes
- Cross-platform consistency validation approaches
- Error detection and recovery procedures

#### Key Documentation Features
- **Self-contained**: Testing suite includes comprehensive standalone documentation
- **Integration-ready**: Subagents automatically enforce testing requirements  
- **Troubleshooting-focused**: Detailed error detection and resolution guidance
- **Example-rich**: Practical usage examples throughout all documentation
- **Future-proof**: Extensible documentation patterns for new features

#### Legacy Items (retained for context)
- [x] Confirmed TypeScript workflow was already fully configuration-driven with no hardcoded values
- [x] Updated `main-branch-post-processing.yml` to use central configuration instead of hardcoded environment variables
- [x] Added setup-config job to main-branch-post-processing workflow for configuration loading
- [x] Validated all workflow syntax and configuration integration across all publishing workflows
- [x] Verified that web-e2e-tests.yml and other workflows properly receive configuration from calling workflows

#### Analysis Results
Upon analysis, the TypeScript publishing workflow (`publish-typescript.yml`) was already **fully configuration-driven**:
- ✅ No hardcoded npm scope or package names
- ✅ Dynamic registry configuration from central config inputs
- ✅ Configuration-driven package naming with suffix support
- ✅ Dynamic credential environment variable selection
- ✅ All configuration received via workflow inputs from orchestrator

#### Technical Changes

**Updated Workflows** - `main-branch-post-processing.yml`:

**Before** (hardcoded environment variables):
```yaml
env:
  NPM_SCOPE: "@vmenon25"
  NPM_PACKAGE_NAME: "mpo-webauthn-client"

publish-client-libraries:
  with:
    npm-scope: "@vmenon25"  # Hardcoded

create-client-releases:
  # Used env.NPM_SCOPE in GitHub release descriptions
```

**After** (configuration-driven):
```yaml
env:
  PUBLISHING_CONFIG_FILE: "config/publishing-config.yml"

jobs:
  setup-config:
    outputs:
      npm-scope: ${{ steps.config.outputs.npm-scope }}
      npm-package-name: ${{ steps.config.outputs.npm-package-name }}

  publish-client-libraries:
    needs: [ setup-config, generate-production-version ]
    with:
      npm-scope: "${{ needs.setup-config.outputs.npm-scope }}"

  create-client-releases:
    needs: [ setup-config, generate-production-version, publish-client-libraries ]
    # Uses needs.setup-config.outputs.npm-scope in GitHub release descriptions
```

#### Configuration Integration
- **YAML Loading**: Added yq-based configuration loading to main-branch-post-processing.yml
- **Job Dependencies**: Updated job dependency chains to include setup-config
- **Output Mapping**: All workflows now use job outputs from central configuration loading
- **Backward Compatibility**: All existing workflow interfaces preserved

#### Benefits Achieved
- **Zero hardcoded npm configuration**: All npm scope and package names come from central config
- **Consistent configuration source**: Single source of truth for all publishing workflows  
- **Maintainable releases**: GitHub release descriptions automatically use correct package names
- **Configuration validation**: Automated validation ensures required configuration exists

#### Validation Results
- [x] Workflow syntax validation passed for all modified workflows
- [x] Central configuration loading logic validated with yq
- [x] Job dependency chains verified for all publishing workflows
- [x] Input/output mapping confirmed between orchestrator and platform workflows