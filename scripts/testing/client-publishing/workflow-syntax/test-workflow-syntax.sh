#!/bin/bash
# Test GitHub Actions workflow syntax validation
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="GitHub Actions Workflow Syntax Validation"
TEST_CATEGORY="workflow-syntax"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Define workflow files to test
declare -a WORKFLOW_FILES=(
    "${WORKFLOWS_DIR}/client-publish.yml"
    "${WORKFLOWS_DIR}/publish-android.yml"
    "${WORKFLOWS_DIR}/publish-typescript.yml"
)

# Test 1: Basic YAML syntax validation for all workflow files
test_workflow_yaml_syntax() {
    log_info "Testing workflow YAML syntax..."
    
    local syntax_errors=0
    
    for workflow_file in "${WORKFLOW_FILES[@]}"; do
        log_debug "Validating syntax for $(basename "$workflow_file")"
        
        if ! check_file_exists "$workflow_file" "workflow file"; then
            log_error "Workflow file not found: $workflow_file"
            ((syntax_errors++))
            continue
        fi
        
        if ! validate_yaml "$workflow_file"; then
            log_error "YAML syntax error in $(basename "$workflow_file")"
            ((syntax_errors++))
        fi
    done
    
    if [[ $syntax_errors -gt 0 ]]; then
        log_error "Found $syntax_errors workflow files with YAML syntax errors"
        return 1
    fi
    
    log_success "All workflow files have valid YAML syntax"
    return 0
}

# Test 2: GitHub Actions specific syntax validation using actionlint
test_github_actions_syntax() {
    log_info "Testing GitHub Actions specific syntax..."
    
    if ! check_tool_available "actionlint"; then
        log_warning "actionlint not available - skipping GitHub Actions syntax validation"
        log_info "Install with: brew install actionlint"
        return 0
    fi
    
    local actionlint_errors=0
    
    for workflow_file in "${WORKFLOW_FILES[@]}"; do
        log_debug "Running actionlint on $(basename "$workflow_file")"
        
        if ! validate_workflow_syntax "$workflow_file"; then
            log_error "GitHub Actions syntax error in $(basename "$workflow_file")"
            ((actionlint_errors++))
        fi
    done
    
    if [[ $actionlint_errors -gt 0 ]]; then
        log_error "Found $actionlint_errors workflow files with GitHub Actions syntax errors"
        return 1
    fi
    
    log_success "All workflow files have valid GitHub Actions syntax"
    return 0
}

# Test 3: Validate workflow structure and required sections
test_workflow_structure() {
    log_info "Testing workflow structure and required sections..."
    
    local structure_errors=0
    
    for workflow_file in "${WORKFLOW_FILES[@]}"; do
        local workflow_name
        workflow_name=$(basename "$workflow_file" .yml)
        
        log_debug "Validating structure for $workflow_name"
        
        # Check for required top-level sections
        local required_sections=("name" "on")
        
        for section in "${required_sections[@]}"; do
            if ! yq eval "has(\"$section\")" "$workflow_file" | grep -q "true"; then
                log_error "Missing required section '$section' in $workflow_name"
                ((structure_errors++))
            fi
        done
        
        # Check for jobs section
        if ! yq eval "has(\"jobs\")" "$workflow_file" | grep -q "true"; then
            log_error "Missing 'jobs' section in $workflow_name"
            ((structure_errors++))
        fi
        
        # For callable workflows, check workflow_call trigger
        if [[ "$workflow_name" != "client-publish" ]]; then
            if ! yq eval ".on | has(\"workflow_call\")" "$workflow_file" | grep -q "true"; then
                log_error "Missing 'workflow_call' trigger in callable workflow $workflow_name"
                ((structure_errors++))
            fi
        fi
    done
    
    if [[ $structure_errors -gt 0 ]]; then
        log_error "Found $structure_errors workflow structure errors"
        return 1
    fi
    
    log_success "All workflow files have valid structure"
    return 0
}

# Test 4: Validate job definitions and structure
test_job_definitions() {
    log_info "Testing job definitions..."
    
    local job_errors=0
    
    for workflow_file in "${WORKFLOW_FILES[@]}"; do
        local workflow_name
        workflow_name=$(basename "$workflow_file" .yml)
        
        log_debug "Validating jobs for $workflow_name"
        
        # Get all job names (filter out comments)
        local jobs
        jobs=$(yq eval '.jobs | keys' "$workflow_file" | grep -v '^#' | grep -v '^[[:space:]]*#')
        
        if [[ "$jobs" == "null" || "$jobs" == "[]" ]]; then
            log_error "No jobs defined in $workflow_name"
            ((job_errors++))
            continue
        fi
        
        # Validate each job has required fields
        while IFS= read -r job_name; do
            if [[ -z "$job_name" || "$job_name" == "null" ]]; then
                continue
            fi
            
            # Remove quotes and hyphens from job name
            job_name=$(echo "$job_name" | sed 's/^[[:space:]]*-[[:space:]]*//' | sed 's/^"//' | sed 's/"$//')
            
            log_debug "  Validating job: $job_name"
            
            # Check for runs-on or uses (one must be present)
            local has_runs_on
            has_runs_on=$(yq eval ".jobs.\"$job_name\" | has(\"runs-on\")" "$workflow_file")
            
            local has_uses
            has_uses=$(yq eval ".jobs.\"$job_name\" | has(\"uses\")" "$workflow_file")
            
            if [[ "$has_runs_on" != "true" && "$has_uses" != "true" ]]; then
                log_error "Job '$job_name' in $workflow_name missing 'runs-on' or 'uses'"
                ((job_errors++))
            fi
            
            # If it's a regular job (not callable workflow), it should have steps
            if [[ "$has_runs_on" == "true" ]]; then
                local has_steps
                has_steps=$(yq eval ".jobs.\"$job_name\" | has(\"steps\")" "$workflow_file")
                
                if [[ "$has_steps" != "true" ]]; then
                    log_error "Job '$job_name' in $workflow_name missing 'steps'"
                    ((job_errors++))
                fi
            fi
            
        done <<< "$jobs"
    done
    
    if [[ $job_errors -gt 0 ]]; then
        log_error "Found $job_errors job definition errors"
        return 1
    fi
    
    log_success "All job definitions are valid"
    return 0
}

# Test 5: Validate environment variable usage patterns
test_environment_variable_usage() {
    log_info "Testing environment variable usage patterns..."
    
    local env_errors=0
    
    for workflow_file in "${WORKFLOW_FILES[@]}"; do
        local workflow_name
        workflow_name=$(basename "$workflow_file" .yml)
        
        log_debug "Validating environment variables for $workflow_name"
        
        # Check for problematic env var usage in conditionals
        local conditional_env_usage
        conditional_env_usage=$(grep -n "if:.*env\." "$workflow_file" || true)
        
        if [[ -n "$conditional_env_usage" ]]; then
            log_error "Found env variable usage in conditional in $workflow_name:"
            echo "$conditional_env_usage" | while IFS= read -r line; do
                log_error "  $line"
            done
            log_error "Use job outputs instead of env vars in conditionals"
            ((env_errors++))
        fi
        
        # Check for proper environment variable references
        local invalid_env_refs
        invalid_env_refs=$(grep -n '\${{ env\.[^}]*\.[^}]* }}' "$workflow_file" || true)
        
        if [[ -n "$invalid_env_refs" ]]; then
            log_error "Found invalid environment variable references in $workflow_name:"
            echo "$invalid_env_refs" | while IFS= read -r line; do
                log_error "  $line"
            done
            ((env_errors++))
        fi
    done
    
    if [[ $env_errors -gt 0 ]]; then
        log_error "Found $env_errors environment variable usage errors"
        return 1
    fi
    
    log_success "Environment variable usage patterns are valid"
    return 0
}

# Test 6: Validate secret references and usage
test_secret_references() {
    log_info "Testing secret references and usage..."
    
    local secret_errors=0
    
    for workflow_file in "${WORKFLOW_FILES[@]}"; do
        local workflow_name
        workflow_name=$(basename "$workflow_file" .yml)
        
        log_debug "Validating secret references for $workflow_name"
        
        # Find all secret references
        local secret_refs
        secret_refs=$(grep -o '\${{ secrets\.[A-Z_][A-Z0-9_]* }}' "$workflow_file" || true)
        
        if [[ -n "$secret_refs" ]]; then
            log_debug "Found secret references in $workflow_name:"
            echo "$secret_refs" | sort -u | while IFS= read -r secret_ref; do
                log_debug "  $secret_ref"
                
                # Extract secret name
                local secret_name
                secret_name=$(echo "$secret_ref" | sed 's/\${{ secrets\.\([A-Z_][A-Z0-9_]*\) }}/\1/')
                
                # Validate secret name format (uppercase with underscores)
                if [[ ! "$secret_name" =~ ^[A-Z][A-Z0-9_]*$ ]]; then
                    log_error "Invalid secret name format: $secret_name in $workflow_name"
                    ((secret_errors++))
                fi
            done
        fi
        
        # Check that callable workflows define their required secrets
        if [[ "$workflow_name" != "client-publish" ]]; then
            # This is a callable workflow, check if it defines secrets section
            local has_secrets_section
            has_secrets_section=$(yq eval ".on.workflow_call | has(\"secrets\")" "$workflow_file")
            
            if [[ "$has_secrets_section" == "true" && -n "$secret_refs" ]]; then
                log_debug "Callable workflow $workflow_name properly defines secrets section"
            elif [[ "$has_secrets_section" != "true" && -n "$secret_refs" ]]; then
                log_warning "Callable workflow $workflow_name uses secrets but doesn't define secrets section"
                log_warning "This may cause issues with secret passing"
            fi
        fi
    done
    
    if [[ $secret_errors -gt 0 ]]; then
        log_error "Found $secret_errors secret reference errors"
        return 1
    fi
    
    log_success "Secret references are valid"
    return 0
}

# Test 7: Validate action references and versions
test_action_references() {
    log_info "Testing action references and versions..."
    
    local action_errors=0
    
    for workflow_file in "${WORKFLOW_FILES[@]}"; do
        local workflow_name
        workflow_name=$(basename "$workflow_file" .yml)
        
        log_debug "Validating action references for $workflow_name"
        
        # Find all action uses
        local action_uses
        action_uses=$(yq eval '.jobs[].steps[]?.uses' "$workflow_file" 2>/dev/null | grep -v "null" || true)
        
        if [[ -n "$action_uses" ]]; then
            echo "$action_uses" | while IFS= read -r action_use; do
                if [[ -z "$action_use" || "$action_use" == "null" ]]; then
                    continue
                fi
                
                log_debug "  Found action: $action_use"
                
                # Check for version pinning (should have @version)
                if [[ ! "$action_use" =~ @[v0-9] ]]; then
                    log_warning "Action not version pinned: $action_use in $workflow_name"
                    log_warning "Consider pinning to specific version for reproducibility"
                fi
                
                # Check for common action patterns
                case "$action_use" in
                    "actions/checkout@"*)
                        log_debug "    Using standard checkout action"
                        ;;
                    "actions/cache@"*)
                        log_debug "    Using standard cache action"
                        ;;
                    "gradle/actions/setup-gradle@"*)
                        log_debug "    Using Gradle setup action"
                        ;;
                    "./."*)
                        log_debug "    Using local callable workflow"
                        ;;
                    *)
                        log_debug "    Using third-party action: $action_use"
                        ;;
                esac
            done
        fi
    done
    
    if [[ $action_errors -gt 0 ]]; then
        log_error "Found $action_errors action reference errors"
        return 1
    fi
    
    log_success "Action references are valid"
    return 0
}

# Test 8: Validate matrix strategy usage
test_matrix_strategies() {
    log_info "Testing matrix strategy usage..."
    
    for workflow_file in "${WORKFLOW_FILES[@]}"; do
        local workflow_name
        workflow_name=$(basename "$workflow_file" .yml)
        
        log_debug "Checking matrix strategies for $workflow_name"
        
        # Check if any jobs use matrix strategy
        local has_matrix
        has_matrix=$(yq eval '.jobs[] | has("strategy")' "$workflow_file" | grep -q "true" && echo "true" || echo "false")
        
        if [[ "$has_matrix" == "true" ]]; then
            log_debug "Found matrix strategy usage in $workflow_name"
            
            # Validate matrix structure
            local matrix_jobs
            matrix_jobs=$(yq eval '.jobs | to_entries | .[] | select(.value | has("strategy")) | .key' "$workflow_file")
            
            while IFS= read -r job_name; do
                if [[ -z "$job_name" || "$job_name" == "null" ]]; then
                    continue
                fi
                
                log_debug "  Job '$job_name' uses matrix strategy"
                
                # Check matrix has proper structure
                local matrix_structure
                matrix_structure=$(yq eval ".jobs.\"$job_name\".strategy.matrix" "$workflow_file")
                
                if [[ "$matrix_structure" == "null" ]]; then
                    log_error "Job '$job_name' has strategy but no matrix defined"
                    return 1
                fi
                
            done <<< "$matrix_jobs"
        else
            log_debug "No matrix strategies found in $workflow_name"
        fi
    done
    
    log_success "Matrix strategy usage is valid"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_workflow_yaml_syntax || test_result=1
    test_github_actions_syntax || test_result=1
    test_workflow_structure || test_result=1
    test_job_definitions || test_result=1
    test_environment_variable_usage || test_result=1
    test_secret_references || test_result=1
    test_action_references || test_result=1
    test_matrix_strategies || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi