#!/bin/bash
# Test workflow input/output mapping validation
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Workflow Input/Output Mapping Validation"
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

# Define workflow relationships
get_workflow_relationships() {
    local caller="$1"
    case "$caller" in
        "client-publish.yml")
            echo "publish-android.yml publish-typescript.yml"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Test 1: Validate callable workflow input definitions
test_callable_workflow_inputs() {
    log_info "Testing callable workflow input definitions..."
    
    local input_errors=0
    
    # Test publish-android.yml inputs
    local android_workflow="${WORKFLOWS_DIR}/publish-android.yml"
    
    if check_file_exists "$android_workflow" "Android publish workflow"; then
        log_debug "Validating Android workflow inputs"
        
        local expected_android_inputs=(
            "client-version"
            "android-group-id"
            "android-artifact-base-id"
            "publish-type"
            "android-repository-url"
            "android-username-env"
            "android-password-env"
            "android-suffix"
        )
        
        for input_name in "${expected_android_inputs[@]}"; do
            local input_defined
            input_defined=$(yq eval ".on.workflow_call.inputs | has(\"$input_name\")" "$android_workflow")
            
            if [[ "$input_defined" != "true" ]]; then
                log_error "Missing required input '$input_name' in Android workflow"
                ((input_errors++))
            else
                log_debug "  Input '$input_name' is defined"
                
                # Check input properties
                local input_required
                input_required=$(yq eval ".on.workflow_call.inputs.\"$input_name\".required" "$android_workflow")
                
                local input_type
                input_type=$(yq eval ".on.workflow_call.inputs.\"$input_name\".type" "$android_workflow")
                
                if [[ "$input_required" != "true" && "$input_required" != "false" ]]; then
                    log_error "Input '$input_name' missing required property in Android workflow"
                    ((input_errors++))
                fi
                
                if [[ "$input_type" == "null" ]]; then
                    log_error "Input '$input_name' missing type property in Android workflow"
                    ((input_errors++))
                fi
            fi
        done
    else
        ((input_errors++))
    fi
    
    # Test publish-typescript.yml inputs
    local typescript_workflow="${WORKFLOWS_DIR}/publish-typescript.yml"
    
    if check_file_exists "$typescript_workflow" "TypeScript publish workflow"; then
        log_debug "Validating TypeScript workflow inputs"
        
        local expected_typescript_inputs=(
            "publish-type"
            "client-version"
            "npm-scope"
            "npm-package-name"
            "npm-registry-url"
            "npm-credential-env"
            "npm-suffix"
            "android-group-id"
        )
        
        for input_name in "${expected_typescript_inputs[@]}"; do
            local input_defined
            input_defined=$(yq eval ".on.workflow_call.inputs | has(\"$input_name\")" "$typescript_workflow")
            
            if [[ "$input_defined" != "true" ]]; then
                log_error "Missing required input '$input_name' in TypeScript workflow"
                ((input_errors++))
            else
                log_debug "  Input '$input_name' is defined"
            fi
        done
    else
        ((input_errors++))
    fi
    
    if [[ $input_errors -gt 0 ]]; then
        log_error "Found $input_errors input definition errors"
        return 1
    fi
    
    log_success "Callable workflow inputs are properly defined"
    return 0
}

# Test 2: Validate callable workflow output definitions
test_callable_workflow_outputs() {
    log_info "Testing callable workflow output definitions..."
    
    local output_errors=0
    
    # Test publish-android.yml outputs
    local android_workflow="${WORKFLOWS_DIR}/publish-android.yml"
    
    if check_file_exists "$android_workflow" "Android publish workflow"; then
        log_debug "Validating Android workflow outputs"
        
        local expected_android_outputs=(
            "published"
            "skipped"
            "package-name"
            "package-full-name"
        )
        
        for output_name in "${expected_android_outputs[@]}"; do
            local output_defined
            output_defined=$(yq eval ".on.workflow_call.outputs | has(\"$output_name\")" "$android_workflow")
            
            if [[ "$output_defined" != "true" ]]; then
                log_error "Missing required output '$output_name' in Android workflow"
                ((output_errors++))
            else
                log_debug "  Output '$output_name' is defined"
                
                # Check output has description and value
                local output_description
                output_description=$(yq eval ".on.workflow_call.outputs.\"$output_name\".description" "$android_workflow")
                
                local output_value
                output_value=$(yq eval ".on.workflow_call.outputs.\"$output_name\".value" "$android_workflow")
                
                if [[ "$output_description" == "null" ]]; then
                    log_error "Output '$output_name' missing description in Android workflow"
                    ((output_errors++))
                fi
                
                if [[ "$output_value" == "null" ]]; then
                    log_error "Output '$output_name' missing value in Android workflow"
                    ((output_errors++))
                fi
            fi
        done
    else
        ((output_errors++))
    fi
    
    # Test publish-typescript.yml outputs
    local typescript_workflow="${WORKFLOWS_DIR}/publish-typescript.yml"
    
    if check_file_exists "$typescript_workflow" "TypeScript publish workflow"; then
        log_debug "Validating TypeScript workflow outputs"
        
        local expected_typescript_outputs=(
            "published"
            "skipped"
            "package-name"
            "package-full-name"
        )
        
        for output_name in "${expected_typescript_outputs[@]}"; do
            local output_defined
            output_defined=$(yq eval ".on.workflow_call.outputs | has(\"$output_name\")" "$typescript_workflow")
            
            if [[ "$output_defined" != "true" ]]; then
                log_error "Missing required output '$output_name' in TypeScript workflow"
                ((output_errors++))
            else
                log_debug "  Output '$output_name' is defined"
            fi
        done
    else
        ((output_errors++))
    fi
    
    if [[ $output_errors -gt 0 ]]; then
        log_error "Found $output_errors output definition errors"
        return 1
    fi
    
    log_success "Callable workflow outputs are properly defined"
    return 0
}

# Test 3: Validate orchestrator workflow input passing
test_orchestrator_input_passing() {
    log_info "Testing orchestrator workflow input passing..."
    
    local orchestrator_workflow="${WORKFLOWS_DIR}/client-publish.yml"
    local passing_errors=0
    
    if ! check_file_exists "$orchestrator_workflow" "orchestrator workflow"; then
        return 1
    fi
    
    # Check that orchestrator passes required inputs to callable workflows
    
    # Check Android workflow call
    log_debug "Validating input passing to Android workflow"
    local android_job_exists
    android_job_exists=$(yq eval '.jobs | has("publish-android")' "$orchestrator_workflow")
    
    if [[ "$android_job_exists" == "true" ]]; then
        local android_inputs
        android_inputs=$(yq eval '.jobs.publish-android.with | keys' "$orchestrator_workflow")
        
        local expected_android_inputs=(
            "publish-type"
            "client-version"
            "android-group-id"
            "android-artifact-base-id"
            "android-repository-url"
            "android-username-env"
            "android-password-env"
            "android-suffix"
        )
        
        for input_name in "${expected_android_inputs[@]}"; do
            local input_passed
            input_passed=$(yq eval ".jobs.publish-android.with | has(\"$input_name\")" "$orchestrator_workflow")
            
            if [[ "$input_passed" != "true" ]]; then
                log_error "Orchestrator not passing '$input_name' to Android workflow"
                ((passing_errors++))
            else
                log_debug "  Input '$input_name' is passed to Android workflow"
            fi
        done
    else
        log_error "Android job not found in orchestrator workflow"
        ((passing_errors++))
    fi
    
    # Check TypeScript workflow call
    log_debug "Validating input passing to TypeScript workflow"
    local typescript_job_exists
    typescript_job_exists=$(yq eval '.jobs | has("publish-typescript")' "$orchestrator_workflow")
    
    if [[ "$typescript_job_exists" == "true" ]]; then
        local expected_typescript_inputs=(
            "publish-type"
            "client-version"
            "npm-scope"
            "npm-package-name"
            "npm-registry-url"
            "npm-credential-env"
            "npm-suffix"
            "android-group-id"
        )
        
        for input_name in "${expected_typescript_inputs[@]}"; do
            local input_passed
            input_passed=$(yq eval ".jobs.publish-typescript.with | has(\"$input_name\")" "$orchestrator_workflow")
            
            if [[ "$input_passed" != "true" ]]; then
                log_error "Orchestrator not passing '$input_name' to TypeScript workflow"
                ((passing_errors++))
            else
                log_debug "  Input '$input_name' is passed to TypeScript workflow"
            fi
        done
    else
        log_error "TypeScript job not found in orchestrator workflow"
        ((passing_errors++))
    fi
    
    if [[ $passing_errors -gt 0 ]]; then
        log_error "Found $passing_errors input passing errors"
        return 1
    fi
    
    log_success "Orchestrator input passing is correct"
    return 0
}

# Test 4: Validate output collection and mapping
test_output_collection_mapping() {
    log_info "Testing output collection and mapping..."
    
    local orchestrator_workflow="${WORKFLOWS_DIR}/client-publish.yml"
    local mapping_errors=0
    
    if ! check_file_exists "$orchestrator_workflow" "orchestrator workflow"; then
        return 1
    fi
    
    # Check that orchestrator workflow defines its own outputs
    log_debug "Validating orchestrator output definitions"
    local orchestrator_outputs
    orchestrator_outputs=$(yq eval '.on.workflow_call.outputs | keys' "$orchestrator_workflow")
    
    local expected_orchestrator_outputs=(
        "typescript-package-name"
        "android-package-name"
        "staging-published"
        "production-published"
        "typescript-published"
        "typescript-skipped"
        "android-published"
        "android-skipped"
    )
    
    for output_name in "${expected_orchestrator_outputs[@]}"; do
        local output_defined
        output_defined=$(yq eval ".on.workflow_call.outputs | has(\"$output_name\")" "$orchestrator_workflow")
        
        if [[ "$output_defined" != "true" ]]; then
            log_error "Missing orchestrator output '$output_name'"
            ((mapping_errors++))
        else
            log_debug "  Orchestrator output '$output_name' is defined"
        fi
    done
    
    # Check that aggregate-results job properly collects outputs
    log_debug "Validating output collection in aggregate-results job"
    local aggregate_job_exists
    aggregate_job_exists=$(yq eval '.jobs | has("aggregate-results")' "$orchestrator_workflow")
    
    if [[ "$aggregate_job_exists" == "true" ]]; then
        # Check that aggregate-results job has outputs section
        local aggregate_outputs_exist
        aggregate_outputs_exist=$(yq eval '.jobs.aggregate-results | has("outputs")' "$orchestrator_workflow")
        
        if [[ "$aggregate_outputs_exist" != "true" ]]; then
            log_error "aggregate-results job missing outputs section"
            ((mapping_errors++))
        else
            # Check specific output mappings
            local aggregate_outputs
            aggregate_outputs=$(yq eval '.jobs.aggregate-results.outputs | keys' "$orchestrator_workflow")
            
            for output_name in "${expected_orchestrator_outputs[@]}"; do
                local output_mapped
                output_mapped=$(yq eval ".jobs.aggregate-results.outputs | has(\"$output_name\")" "$orchestrator_workflow")
                
                if [[ "$output_mapped" != "true" ]]; then
                    log_error "Output '$output_name' not mapped in aggregate-results job"
                    ((mapping_errors++))
                fi
            done
        fi
    else
        log_error "aggregate-results job not found in orchestrator workflow"
        ((mapping_errors++))
    fi
    
    if [[ $mapping_errors -gt 0 ]]; then
        log_error "Found $mapping_errors output mapping errors"
        return 1
    fi
    
    log_success "Output collection and mapping is correct"
    return 0
}

# Test 5: Validate job dependency configuration
test_job_dependency_configuration() {
    log_info "Testing job dependency configuration..."
    
    local orchestrator_workflow="${WORKFLOWS_DIR}/client-publish.yml"
    local dependency_errors=0
    
    if ! check_file_exists "$orchestrator_workflow" "orchestrator workflow"; then
        return 1
    fi
    
    # Check setup-config job dependencies
    log_debug "Validating setup-config job dependencies"
    local setup_config_needs
    setup_config_needs=$(yq eval '.jobs.setup-config.needs // []' "$orchestrator_workflow")
    
    # setup-config should not need other jobs (or only validate-inputs)
    if [[ "$setup_config_needs" != "[]" && "$setup_config_needs" != "null" ]]; then
        log_debug "setup-config has dependencies: $setup_config_needs"
        # This is acceptable if it depends on validate-inputs
    fi
    
    # Check publish jobs dependencies
    log_debug "Validating publish job dependencies"
    local android_needs
    android_needs=$(yq eval '.jobs.publish-android.needs' "$orchestrator_workflow")
    
    local typescript_needs
    typescript_needs=$(yq eval '.jobs.publish-typescript.needs' "$orchestrator_workflow")
    
    # Both should depend on setup-config and validate-inputs
    local expected_dependencies=("validate-inputs" "setup-config")
    
    for dep in "${expected_dependencies[@]}"; do
        if [[ ! "$android_needs" =~ $dep ]]; then
            log_error "Android job missing dependency on '$dep'"
            ((dependency_errors++))
        fi
        
        if [[ ! "$typescript_needs" =~ $dep ]]; then
            log_error "TypeScript job missing dependency on '$dep'"
            ((dependency_errors++))
        fi
    done
    
    # Check aggregate-results dependencies
    log_debug "Validating aggregate-results job dependencies"
    local aggregate_needs
    aggregate_needs=$(yq eval '.jobs.aggregate-results.needs' "$orchestrator_workflow")
    
    local expected_aggregate_dependencies=("validate-inputs" "setup-config" "publish-typescript" "publish-android")
    
    for dep in "${expected_aggregate_dependencies[@]}"; do
        if [[ ! "$aggregate_needs" =~ $dep ]]; then
            log_error "aggregate-results job missing dependency on '$dep'"
            ((dependency_errors++))
        fi
    done
    
    if [[ $dependency_errors -gt 0 ]]; then
        log_error "Found $dependency_errors job dependency errors"
        return 1
    fi
    
    log_success "Job dependency configuration is correct"
    return 0
}

# Test 6: Validate input reference patterns
test_input_reference_patterns() {
    log_info "Testing input reference patterns..."
    
    local reference_errors=0
    
    for workflow_file in "${WORKFLOW_FILES[@]}"; do
        local workflow_name
        workflow_name=$(basename "$workflow_file" .yml)
        
        log_debug "Validating input references for $workflow_name"
        
        # Find all input references
        local input_refs
        input_refs=$(grep -o '\${{ inputs\.[a-zA-Z-][a-zA-Z0-9-]* }}' "$workflow_file" || true)
        
        if [[ -n "$input_refs" ]]; then
            echo "$input_refs" | sort -u | while IFS= read -r input_ref; do
                # Extract input name
                local input_name
                input_name=$(echo "$input_ref" | sed 's/\${{ inputs\.\([a-zA-Z-][a-zA-Z0-9-]*\) }}/\1/')
                
                log_debug "  Found input reference: $input_name"
                
                # For callable workflows, verify the input is defined
                if [[ "$workflow_name" != "client-publish" ]]; then
                    local input_defined
                    input_defined=$(yq eval ".on.workflow_call.inputs | has(\"$input_name\")" "$workflow_file")
                    
                    if [[ "$input_defined" != "true" ]]; then
                        log_error "Input '$input_name' referenced but not defined in $workflow_name"
                        ((reference_errors++))
                    fi
                fi
            done
        fi
    done
    
    if [[ $reference_errors -gt 0 ]]; then
        log_error "Found $reference_errors input reference errors"
        return 1
    fi
    
    log_success "Input reference patterns are valid"
    return 0
}

# Test 7: Validate output reference patterns
test_output_reference_patterns() {
    log_info "Testing output reference patterns..."
    
    local orchestrator_workflow="${WORKFLOWS_DIR}/client-publish.yml"
    local reference_errors=0
    
    if ! check_file_exists "$orchestrator_workflow" "orchestrator workflow"; then
        return 1
    fi
    
    # Find all job output references in orchestrator
    local output_refs
    output_refs=$(grep -o '\${{ needs\.[a-zA-Z-][a-zA-Z0-9-]*\.outputs\.[a-zA-Z-][a-zA-Z0-9-]* }}' "$orchestrator_workflow" || true)
    
    if [[ -n "$output_refs" ]]; then
        echo "$output_refs" | sort -u | while IFS= read -r output_ref; do
            log_debug "Found output reference: $output_ref"
            
            # Extract job name and output name
            local job_name
            job_name=$(echo "$output_ref" | sed 's/\${{ needs\.\([a-zA-Z-][a-zA-Z0-9-]*\)\.outputs\.[a-zA-Z-][a-zA-Z0-9-]* }}/\1/')
            
            local output_name
            output_name=$(echo "$output_ref" | sed 's/\${{ needs\.[a-zA-Z-][a-zA-Z0-9-]*\.outputs\.\([a-zA-Z-][a-zA-Z0-9-]*\) }}/\1/')
            
            # Check that the job exists
            local job_exists
            job_exists=$(yq eval ".jobs | has(\"$job_name\")" "$orchestrator_workflow")
            
            if [[ "$job_exists" != "true" ]]; then
                log_error "Referenced job '$job_name' does not exist"
                ((reference_errors++))
                continue
            fi
            
            # For callable workflow jobs, we can't easily validate output names without complex parsing
            # But we can check if it's a known callable workflow
            case "$job_name" in
                "publish-android"|"publish-typescript")
                    log_debug "  Referencing callable workflow output: $job_name.$output_name"
                    ;;
                "setup-config"|"validate-inputs"|"aggregate-results")
                    log_debug "  Referencing internal job output: $job_name.$output_name"
                    ;;
                *)
                    log_warning "Unknown job reference: $job_name"
                    ;;
            esac
        done
    fi
    
    if [[ $reference_errors -gt 0 ]]; then
        log_error "Found $reference_errors output reference errors"
        return 1
    fi
    
    log_success "Output reference patterns are valid"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_callable_workflow_inputs || test_result=1
    test_callable_workflow_outputs || test_result=1
    test_orchestrator_input_passing || test_result=1
    test_output_collection_mapping || test_result=1
    test_job_dependency_configuration || test_result=1
    test_input_reference_patterns || test_result=1
    test_output_reference_patterns || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi