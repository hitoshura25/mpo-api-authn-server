#!/bin/bash
# Test dynamic yq query construction and environment-specific data extraction
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Dynamic Query Construction and Environment-Specific Data Extraction"
TEST_CATEGORY="environment-selection"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Dynamic environment query construction
test_dynamic_environment_queries() {
    log_info "Testing dynamic environment query construction..."
    
    # Test that queries can be dynamically constructed based on environment type
    local environments=("staging" "production")
    
    for env in "${environments[@]}"; do
        log_debug "Testing dynamic queries for environment: $env"
        
        # Construct queries dynamically
        local android_url_query=".repositories.${env}.android.url"
        local npm_registry_query=".repositories.${env}.npm.registry"
        local android_suffix_query=".naming.${env}.androidSuffix"
        local npm_suffix_query=".naming.${env}.npmSuffix"
        
        # Execute dynamic queries
        local android_url
        android_url=$(yq eval "$android_url_query" "$CONFIG_FILE")
        
        local npm_registry
        npm_registry=$(yq eval "$npm_registry_query" "$CONFIG_FILE")
        
        local android_suffix
        android_suffix=$(yq eval "$android_suffix_query" "$CONFIG_FILE")
        
        local npm_suffix
        npm_suffix=$(yq eval "$npm_suffix_query" "$CONFIG_FILE")
        
        # Validate results are not null
        if [[ "$android_url" == "null" || -z "$android_url" ]]; then
            log_error "Dynamic query for Android URL failed for environment: $env"
            log_error "Query: $android_url_query"
            return 1
        fi
        
        if [[ "$npm_registry" == "null" || -z "$npm_registry" ]]; then
            log_error "Dynamic query for npm registry failed for environment: $env"
            log_error "Query: $npm_registry_query"
            return 1
        fi
        
        # Validate environment-specific values
        if [[ "$env" == "staging" ]]; then
            if [[ ! "$android_url" =~ github\.com ]]; then
                log_error "Staging Android URL should contain github.com"
                log_error "Got: $android_url"
                return 1
            fi
            
            if [[ "$npm_registry" != "https://npm.pkg.github.com" ]]; then
                log_error "Staging npm registry should be GitHub Packages"
                log_error "Got: $npm_registry"
                return 1
            fi
            
            if [[ "$android_suffix" != "-staging" ]]; then
                log_error "Staging Android suffix should be '-staging'"
                log_error "Got: '$android_suffix'"
                return 1
            fi
        fi
        
        if [[ "$env" == "production" ]]; then
            if [[ ! "$android_url" =~ sonatype\.com ]]; then
                log_error "Production Android URL should contain sonatype.com"
                log_error "Got: $android_url"
                return 1
            fi
            
            if [[ "$npm_registry" != "https://registry.npmjs.org" ]]; then
                log_error "Production npm registry should be npmjs.org"
                log_error "Got: $npm_registry"
                return 1
            fi
            
            if [[ "$android_suffix" != "" ]]; then
                log_error "Production Android suffix should be empty"
                log_error "Got: '$android_suffix'"
                return 1
            fi
        fi
        
        log_debug "Dynamic queries successful for environment: $env"
    done
    
    log_success "Dynamic environment query construction validated"
    return 0
}

# Test 2: Credential environment variable extraction
test_credential_env_var_extraction() {
    log_info "Testing credential environment variable extraction..."
    
    # Test dynamic extraction of credential environment variable names
    local environments=("staging" "production")
    local platforms=("android" "npm")
    
    for env in "${environments[@]}"; do
        for platform in "${platforms[@]}"; do
            log_debug "Testing credential extraction for $env/$platform"
            
            if [[ "$platform" == "android" ]]; then
                local username_query=".repositories.${env}.${platform}.credentials.usernameEnv"
                local password_query=".repositories.${env}.${platform}.credentials.passwordEnv"
                
                local username_env
                username_env=$(yq eval "$username_query" "$CONFIG_FILE")
                
                local password_env
                password_env=$(yq eval "$password_query" "$CONFIG_FILE")
                
                if [[ "$username_env" == "null" || -z "$username_env" ]]; then
                    log_error "Failed to extract username env var for $env/$platform"
                    log_error "Query: $username_query"
                    return 1
                fi
                
                if [[ "$password_env" == "null" || -z "$password_env" ]]; then
                    log_error "Failed to extract password env var for $env/$platform"
                    log_error "Query: $password_query"
                    return 1
                fi
                
                log_debug "$env/$platform username env: $username_env"
                log_debug "$env/$platform password env: $password_env"
            fi
            
            if [[ "$platform" == "npm" ]]; then
                local token_query=".repositories.${env}.${platform}.credentials.tokenEnv"
                
                local token_env
                token_env=$(yq eval "$token_query" "$CONFIG_FILE")
                
                if [[ "$token_env" == "null" || -z "$token_env" ]]; then
                    log_error "Failed to extract token env var for $env/$platform"
                    log_error "Query: $token_query"
                    return 1
                fi
                
                log_debug "$env/$platform token env: $token_env"
            fi
        done
    done
    
    log_success "Credential environment variable extraction validated"
    return 0
}

# Test 3: Package naming component extraction
test_package_naming_extraction() {
    log_info "Testing package naming component extraction..."
    
    # Test extraction of package naming components for dynamic package name construction
    local base_android_group
    base_android_group=$(yq eval '.packages.android.groupId' "$CONFIG_FILE")
    
    local base_android_artifact
    base_android_artifact=$(yq eval '.packages.android.baseArtifactId' "$CONFIG_FILE")
    
    local base_npm_scope
    base_npm_scope=$(yq eval '.packages.typescript.scope' "$CONFIG_FILE")
    
    local base_npm_package
    base_npm_package=$(yq eval '.packages.typescript.basePackageName' "$CONFIG_FILE")
    
    # Validate base components
    if [[ "$base_android_group" == "null" || -z "$base_android_group" ]]; then
        log_error "Failed to extract Android group ID"
        return 1
    fi
    
    if [[ "$base_android_artifact" == "null" || -z "$base_android_artifact" ]]; then
        log_error "Failed to extract Android base artifact ID"
        return 1
    fi
    
    if [[ "$base_npm_scope" == "null" || -z "$base_npm_scope" ]]; then
        log_error "Failed to extract npm scope"
        return 1
    fi
    
    if [[ "$base_npm_package" == "null" || -z "$base_npm_package" ]]; then
        log_error "Failed to extract npm base package name"
        return 1
    fi
    
    # Test dynamic suffix extraction and package name construction
    local environments=("staging" "production")
    
    for env in "${environments[@]}"; do
        local android_suffix_query=".naming.${env}.androidSuffix"
        local npm_suffix_query=".naming.${env}.npmSuffix"
        
        local android_suffix
        android_suffix=$(yq eval "$android_suffix_query" "$CONFIG_FILE")
        
        local npm_suffix
        npm_suffix=$(yq eval "$npm_suffix_query" "$CONFIG_FILE")
        
        # Construct full package names
        local full_android_artifact="${base_android_artifact}${android_suffix}"
        local full_android_coordinates="${base_android_group}:${full_android_artifact}"
        
        local full_npm_package="${base_npm_package}${npm_suffix}"
        local full_npm_name="${base_npm_scope}/${full_npm_package}"
        
        log_debug "$env Android coordinates: $full_android_coordinates"
        log_debug "$env npm package: $full_npm_name"
        
        # Validate constructed names
        if [[ "$env" == "staging" ]]; then
            if [[ ! "$full_android_artifact" =~ -staging$ ]]; then
                log_error "Staging Android artifact should end with '-staging'"
                log_error "Got: $full_android_artifact"
                return 1
            fi
            
            if [[ ! "$full_npm_package" =~ -staging$ ]]; then
                log_error "Staging npm package should end with '-staging'"
                log_error "Got: $full_npm_package"
                return 1
            fi
        fi
        
        if [[ "$env" == "production" ]]; then
            if [[ "$full_android_artifact" =~ -staging$ ]]; then
                log_error "Production Android artifact should not end with '-staging'"
                log_error "Got: $full_android_artifact"
                return 1
            fi
            
            if [[ "$full_npm_package" =~ -staging$ ]]; then
                log_error "Production npm package should not end with '-staging'"
                log_error "Got: $full_npm_package"
                return 1
            fi
        fi
    done
    
    log_success "Package naming component extraction validated"
    return 0
}

# Test 4: Nested query construction and validation
test_nested_query_construction() {
    log_info "Testing nested query construction and validation..."
    
    # Test complex nested queries that might be used in workflow scripts
    local test_queries=(
        ".repositories.staging.android.credentials"
        ".repositories.production.npm.credentials"
        ".naming.staging"
        ".naming.production"
        ".packages.android"
        ".packages.typescript"
    )
    
    for query in "${test_queries[@]}"; do
        log_debug "Testing nested query: $query"
        
        local result
        result=$(yq eval "$query" "$CONFIG_FILE")
        
        if [[ "$result" == "null" ]]; then
            log_error "Nested query returned null: $query"
            return 1
        fi
        
        # Validate that the result is a proper object/map for credential and package queries
        if [[ "$query" =~ credentials$ ]] || [[ "$query" =~ \.(android|typescript|staging|production)$ ]]; then
            local result_type
            result_type=$(yq eval "$query | type" "$CONFIG_FILE")
            
            if [[ "$result_type" != "!!map" ]]; then
                log_error "Query should return a map/object: $query"
                log_error "Got type: $result_type"
                return 1
            fi
        fi
        
        log_debug "Nested query successful: $query"
    done
    
    log_success "Nested query construction validated"
    return 0
}

# Test 5: Query result transformation and processing
test_query_result_transformation() {
    log_info "Testing query result transformation and processing..."
    
    # Test that query results can be processed and transformed as needed
    
    # Test 1: Extract all environment names dynamically
    local all_repository_envs
    all_repository_envs=$(yq eval '.repositories | keys' "$CONFIG_FILE" | grep -v '^#' | sed 's/^- //')
    
    local expected_envs=("staging" "production")
    local found_envs=()
    
    while IFS= read -r env; do
        if [[ -n "$env" && "$env" != "null" ]]; then
            found_envs+=("$env")
        fi
    done <<< "$all_repository_envs"
    
    for expected_env in "${expected_envs[@]}"; do
        local env_found=false
        for found_env in "${found_envs[@]}"; do
            if [[ "$found_env" == "$expected_env" ]]; then
                env_found=true
                break
            fi
        done
        
        if [[ "$env_found" != "true" ]]; then
            log_error "Expected environment not found in repository configuration: $expected_env"
            return 1
        fi
    done
    
    # Test 2: Extract all platform names dynamically
    local staging_platforms
    staging_platforms=$(yq eval '.repositories.staging | keys' "$CONFIG_FILE" | grep -v '^#' | sed 's/^- //')
    
    local expected_platforms=("android" "npm")
    local found_platforms=()
    
    while IFS= read -r platform; do
        if [[ -n "$platform" && "$platform" != "null" ]]; then
            found_platforms+=("$platform")
        fi
    done <<< "$staging_platforms"
    
    for expected_platform in "${expected_platforms[@]}"; do
        local platform_found=false
        for found_platform in "${found_platforms[@]}"; do
            if [[ "$found_platform" == "$expected_platform" ]]; then
                platform_found=true
                break
            fi
        done
        
        if [[ "$platform_found" != "true" ]]; then
            log_error "Expected platform not found in staging configuration: $expected_platform"
            return 1
        fi
    done
    
    # Test 3: URL pattern validation through query transformation
    local all_urls=()
    
    for env in "${expected_envs[@]}"; do
        for platform in "${expected_platforms[@]}"; do
            if [[ "$platform" == "android" ]]; then
                local url_query=".repositories.${env}.${platform}.url"
                local url
                url=$(yq eval "$url_query" "$CONFIG_FILE")
                all_urls+=("$url")
            fi
            
            if [[ "$platform" == "npm" ]]; then
                local registry_query=".repositories.${env}.${platform}.registry"
                local registry
                registry=$(yq eval "$registry_query" "$CONFIG_FILE")
                all_urls+=("$registry")
            fi
        done
    done
    
    # Validate all URLs are HTTPS
    for url in "${all_urls[@]}"; do
        if [[ ! "$url" =~ ^https:// ]]; then
            log_error "All repository URLs should use HTTPS: $url"
            return 1
        fi
    done
    
    log_success "Query result transformation and processing validated"
    return 0
}

# Test 6: Environment-specific query optimization
test_environment_query_optimization() {
    log_info "Testing environment-specific query optimization..."
    
    # Test that queries can be optimized to extract only necessary data for specific environments
    
    # Test 1: Extract only staging configuration
    local staging_only_query=".repositories.staging"
    local staging_config
    staging_config=$(yq eval "$staging_only_query" "$CONFIG_FILE")
    
    # Verify staging config doesn't accidentally include production data
    if echo "$staging_config" | grep -q "registry.npmjs.org"; then
        log_error "Staging-only query accidentally included production npm registry"
        return 1
    fi
    
    if echo "$staging_config" | grep -q "sonatype.com"; then
        log_error "Staging-only query accidentally included production Maven repository"
        return 1
    fi
    
    # Test 2: Extract only production configuration
    local production_only_query=".repositories.production"
    local production_config
    production_config=$(yq eval "$production_only_query" "$CONFIG_FILE")
    
    # Verify production config doesn't accidentally include staging data
    if echo "$production_config" | grep -q "npm.pkg.github.com"; then
        log_error "Production-only query accidentally included staging npm registry"
        return 1
    fi
    
    if echo "$production_config" | grep -q "maven.pkg.github.com"; then
        log_error "Production-only query accidentally included staging Maven repository"
        return 1
    fi
    
    # Test 3: Platform-specific extraction
    local android_only_query=".repositories.staging.android"
    local android_config
    android_config=$(yq eval "$android_only_query" "$CONFIG_FILE")
    
    # Verify Android config doesn't include npm-specific fields
    if echo "$android_config" | grep -q "registry"; then
        log_error "Android-only query accidentally included npm registry field"
        return 1
    fi
    
    local npm_only_query=".repositories.staging.npm"
    local npm_config
    npm_config=$(yq eval "$npm_only_query" "$CONFIG_FILE")
    
    # Verify npm config doesn't include Android-specific fields
    if echo "$npm_config" | grep -q "usernameEnv"; then
        log_error "npm-only query accidentally included Android username field"
        return 1
    fi
    
    if echo "$npm_config" | grep -q "passwordEnv"; then
        log_error "npm-only query accidentally included Android password field"
        return 1
    fi
    
    log_success "Environment-specific query optimization validated"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_dynamic_environment_queries || test_result=1
    test_credential_env_var_extraction || test_result=1
    test_package_naming_extraction || test_result=1
    test_nested_query_construction || test_result=1
    test_query_result_transformation || test_result=1
    test_environment_query_optimization || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi