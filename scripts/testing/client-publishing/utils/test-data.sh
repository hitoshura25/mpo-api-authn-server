#!/bin/bash
# Test data and scenarios for client publishing testing suite
set -euo pipefail

# Test data configuration
# Using functions instead of associative arrays for bash compatibility

get_test_scenario() {
    local scenario_name="$1"
    case "$scenario_name" in
        "valid_staging_config")
            cat << 'EOF'
packages:
  android:
    groupId: "io.github.hitoshura25"
    baseArtifactId: "mpo-webauthn-android-client"
  typescript:
    scope: "@vmenon25"
    basePackageName: "mpo-webauthn-client"

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
        tokenEnv: "GITHUB_TOKEN"
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

naming:
  staging:
    androidSuffix: "-staging"
    npmSuffix: "-staging"
  production:
    androidSuffix: ""
    npmSuffix: ""

metadata:
  projectUrl: "https://github.com/hitoshura25/mpo-api-authn-server"
  description: "Generated client libraries for MPO WebAuthn API"
  license: "MIT"
  author:
    name: "Hitoshura"
    email: "hitoshura25@users.noreply.github.com"
    id: "hitoshura25"

schema:
  version: "1.0"
  lastUpdated: "2025-01-16"
EOF
            ;;
        "missing_packages_section")
            cat << 'EOF'
repositories:
  staging:
    android:
      url: "https://maven.pkg.github.com/test/repo"
      credentials:
        usernameEnv: "USER"
        passwordEnv: "PASS"
naming:
  staging:
    androidSuffix: "-staging"
EOF
            ;;
        "missing_android_config")
            cat << 'EOF'
packages:
  typescript:
    scope: "@test"
    basePackageName: "test-client"
repositories:
  staging:
    npm:
      registry: "https://npm.pkg.github.com"
      credentials:
        tokenEnv: "TOKEN"
EOF
            ;;
        "invalid_yaml_syntax")
            cat << 'EOF'
packages:
  android:
    groupId: "test.group"
    baseArtifactId: "test-artifact"
  typescript:
    scope: "@test"
    basePackageName: "test-client"
repositories:
  staging:
    android:
      url: "https://maven.pkg.github.com/test/repo"
      credentials:
        usernameEnv: "USER"
        passwordEnv: "PASS"
    npm:
      registry: "https://npm.pkg.github.com"
      credentials:
        tokenEnv: "TOKEN"
naming:
  staging:
    androidSuffix: "-staging"
    npmSuffix: "-staging"
  # Invalid YAML - missing colon after production
  production
    androidSuffix: ""
    npmSuffix: ""
EOF
            ;;
        "null_values_config")
            cat << 'EOF'
packages:
  android:
    groupId: null
    baseArtifactId: "test-artifact"
  typescript:
    scope: "@test"
    basePackageName: null
repositories:
  staging:
    android:
      url: null
      credentials:
        usernameEnv: "USER"
        passwordEnv: "PASS"
EOF
            ;;
        *)
            echo ""
            ;;
    esac
}

get_workflow_input() {
    local input_name="$1"
    case "$input_name" in
        "staging_pr_publish")
            cat << 'EOF'
publish-type: staging
client-version: 1.0.0-pr.123.456
workflow-identifier: 123
npm-scope: @vmenon25
EOF
            ;;
        "staging_main_publish")
            cat << 'EOF'
publish-type: staging
client-version: 1.0.0-main.789
workflow-identifier: main
npm-scope: @vmenon25
EOF
            ;;
        "production_publish")
            cat << 'EOF'
publish-type: production
client-version: 1.2.3
workflow-identifier: ""
npm-scope: @vmenon25
EOF
            ;;
        "invalid_publish_type")
            cat << 'EOF'
publish-type: invalid
client-version: 1.0.0
workflow-identifier: 123
npm-scope: @vmenon25
EOF
            ;;
        "missing_version")
            cat << 'EOF'
publish-type: staging
client-version: ""
workflow-identifier: 123
npm-scope: @vmenon25
EOF
            ;;
        *)
            echo ""
            ;;
    esac
}

# Test version formats
get_valid_versions() {
    echo "1.0.0 1.2.3 2.0.0-alpha 1.0.0-beta.1 1.0.0-rc.1 1.0.0-pr.123.456 1.0.0-main.789 1.0.0-alpha-beta 1.0.0-snapshot 1.0.0-dev.1"
}

get_invalid_versions() {
    echo "1.0 1.0.0.0 1.0.0- \"\" abc 1.0.0-α 1.0.0-beta.. 1.0.0-beta. v1.0.0 1.0.0+"
}

get_env_combination() {
    local combination_name="$1"
    case "$combination_name" in
        "staging_complete")
            cat << 'EOF'
GITHUB_REPOSITORY=hitoshura25/mpo-api-authn-server
GITHUB_ACTOR=test-user
GITHUB_TOKEN=mock-github-token
ANDROID_PUBLISH_USER=staging-user
ANDROID_PUBLISH_TOKEN=staging-token
NPM_PUBLISH_TOKEN=staging-npm-token
EOF
            ;;
        "production_complete")
            cat << 'EOF'
GITHUB_REPOSITORY=hitoshura25/mpo-api-authn-server
GITHUB_ACTOR=test-user
GITHUB_TOKEN=mock-github-token
CENTRAL_PORTAL_USERNAME=central-user
CENTRAL_PORTAL_PASSWORD=central-password
NPM_PUBLISH_TOKEN=production-npm-token
SIGNING_KEY=mock-signing-key
SIGNING_PASSWORD=mock-signing-password
EOF
            ;;
        "missing_credentials")
            cat << 'EOF'
GITHUB_REPOSITORY=hitoshura25/mpo-api-authn-server
GITHUB_ACTOR=test-user
GITHUB_TOKEN=mock-github-token
EOF
            ;;
        *)
            echo ""
            ;;
    esac
}

get_package_naming_test() {
    local test_name="$1"
    case "$test_name" in
        "staging_android")
            echo "groupId: io.github.hitoshura25
baseArtifactId: mpo-webauthn-android-client
suffix: -staging
expected: io.github.hitoshura25:mpo-webauthn-android-client-staging"
            ;;
        "production_android")
            echo "groupId: io.github.hitoshura25
baseArtifactId: mpo-webauthn-android-client
suffix: \"\"
expected: io.github.hitoshura25:mpo-webauthn-android-client"
            ;;
        "staging_npm")
            echo "scope: @vmenon25
basePackageName: mpo-webauthn-client
suffix: -staging
expected: @vmenon25/mpo-webauthn-client-staging"
            ;;
        "production_npm")
            echo "scope: @vmenon25
basePackageName: mpo-webauthn-client
suffix: \"\"
expected: @vmenon25/mpo-webauthn-client"
            ;;
        *)
            echo ""
            ;;
    esac
}

get_repository_test() {
    local test_name="$1"
    case "$test_name" in
        "github_packages_android")
            echo "url: https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server
expected_type: github_packages
expected_valid: true"
            ;;
        "maven_central_android")
            echo "url: https://ossrh-staging-api.central.sonatype.com/service/local/staging/deploy/maven2/
expected_type: maven_central
expected_valid: true"
            ;;
        "npm_registry")
            echo "url: https://registry.npmjs.org
expected_type: npm_public
expected_valid: true"
            ;;
        "github_packages_npm")
            echo "url: https://npm.pkg.github.com
expected_type: github_packages_npm
expected_valid: true"
            ;;
        "invalid_url")
            echo "url: not-a-valid-url
expected_type: invalid
expected_valid: false"
            ;;
        *)
            echo ""
            ;;
    esac
}

get_mock_registry_response() {
    local response_name="$1"
    case "$response_name" in
        "version_exists")
            cat << 'EOF'
{
  "name": "@vmenon25/mpo-webauthn-client",
  "versions": {
    "1.0.0": {},
    "1.0.1": {},
    "1.0.2-pr.123.456": {}
  }
}
EOF
            ;;
        "version_not_exists")
            cat << 'EOF'
{
  "name": "@vmenon25/mpo-webauthn-client",
  "versions": {
    "1.0.0": {},
    "1.0.1": {}
  }
}
EOF
            ;;
        "package_not_exists")
            cat << 'EOF'
{
  "error": "Package not found"
}
EOF
            ;;
        *)
            echo ""
            ;;
    esac
}

# Template content functions
get_gradle_template_android() {
    cat << 'EOF'
plugins {
    id "java-library"
    id "maven-publish"
    id "signing"
}

group = "GROUP_ID_PLACEHOLDER"
version = "VERSION_PLACEHOLDER"

publishing {
    publications {
        maven(MavenPublication) {
            groupId = "GROUP_ID_PLACEHOLDER"
            artifactId = "ARTIFACT_ID_PLACEHOLDER"
            version = "VERSION_PLACEHOLDER"
            
            from components.java
        }
    }
    
    repositories {
        maven {
            name = "PublishingRepository"
            url = "REPOSITORY_URL_PLACEHOLDER"
            credentials {
                username = project.findProperty("PublishingRepositoryUsername") ?: System.getenv("USERNAME_ENV_PLACEHOLDER")
                password = project.findProperty("PublishingRepositoryPassword") ?: System.getenv("PASSWORD_ENV_PLACEHOLDER")
            }
        }
    }
}

signing {
    required { gradle.taskGraph.hasTask("publish") }
    sign publishing.publications.maven
}
EOF
}

get_package_json_template() {
    cat << 'EOF'
{
  "name": "NPM_PACKAGE_NAME_PLACEHOLDER",
  "version": "VERSION_PLACEHOLDER",
  "description": "Generated TypeScript client for MPO WebAuthn API",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "prepare": "npm run build"
  },
  "publishConfig": {
    "registry": "REGISTRY_URL_PLACEHOLDER"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/hitoshura25/mpo-api-authn-server.git"
  },
  "author": "Hitoshura <hitoshura25@users.noreply.github.com>",
  "license": "MIT"
}
EOF
}

create_test_config_file() {
    local scenario_name="$1"
    local output_file="$2"
    
    local config_content
    config_content=$(get_test_scenario "$scenario_name")
    
    if [[ -z "$config_content" ]]; then
        log_error "Unknown test scenario: $scenario_name"
        return 1
    fi
    
    echo "$config_content" > "$output_file"
    log_debug "Created test config file: $output_file (scenario: $scenario_name)"
}

setup_test_environment_vars() {
    local combination_name="$1"
    
    local env_vars
    env_vars=$(get_env_combination "$combination_name")
    
    if [[ -z "$env_vars" ]]; then
        log_error "Unknown environment combination: $combination_name"
        return 1
    fi
    
    # Parse and export environment variables
    while IFS= read -r line; do
        if [[ -n "$line" && "$line" == *"="* ]]; then
            local var_name="${line%%=*}"
            local var_value="${line#*=}"
            
            if [[ -n "$var_name" && -n "$var_value" ]]; then
                export "$var_name=$var_value"
                log_debug "Set environment variable: $var_name"
            fi
        fi
    done <<< "$env_vars"
}

validate_test_version() {
    local version="$1"
    local should_be_valid="$2"
    
    local valid_versions=$(get_valid_versions)
    local is_valid=false
    
    for valid_version in $valid_versions; do
        if [[ "$version" == "$valid_version" ]]; then
            is_valid=true
            break
        fi
    done
    
    if [[ "$should_be_valid" == "true" ]]; then
        if [[ "$is_valid" == "true" ]]; then
            log_debug "Version validation passed: $version (should be valid)"
            return 0
        else
            log_error "Version validation failed: $version (should be valid but isn't)"
            return 1
        fi
    else
        if [[ "$is_valid" == "false" ]]; then
            log_debug "Version validation passed: $version (should be invalid)"
            return 0
        else
            log_error "Version validation failed: $version (should be invalid but isn't)"
            return 1
        fi
    fi
}

generate_template_with_substitutions() {
    local template_type="$1"  # "android" or "typescript"
    local output_file="$2"
    shift 2
    local substitutions=("$@")  # Array of "PLACEHOLDER=value" strings
    
    local template_content
    case "$template_type" in
        "android")
            template_content=$(get_gradle_template_android)
            ;;
        "typescript")
            template_content=$(get_package_json_template)
            ;;
        *)
            log_error "Unknown template type: $template_type"
            return 1
            ;;
    esac
    
    # Apply substitutions
    local result="$template_content"
    for substitution in "${substitutions[@]}"; do
        local placeholder="${substitution%%=*}"
        local value="${substitution#*=}"
        result="${result//$placeholder/$value}"
    done
    
    echo "$result" > "$output_file"
    log_debug "Generated $template_type template with substitutions: $output_file"
}

# Export functions for use in test scripts
export -f get_test_scenario get_workflow_input get_env_combination
export -f get_package_naming_test get_repository_test get_mock_registry_response
export -f get_gradle_template_android get_package_json_template
export -f create_test_config_file setup_test_environment_vars
export -f validate_test_version generate_template_with_substitutions
export -f get_valid_versions get_invalid_versions