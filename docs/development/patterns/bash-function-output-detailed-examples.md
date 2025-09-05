# Bash Function Output Redirection - Detailed Examples

**Extracted from CLAUDE.md for detailed reference**  
**Core pattern remains in CLAUDE.md**

## Comprehensive Bash Function Output Handling

### Problem: Debug Output Pollution

```bash
# ❌ PROBLEMATIC: Debug output pollutes return value
extract_image_tag() {
    echo "🔧 Processing image tags..."  # Goes to stdout - PROBLEM!
    echo "Input: $1"                    # Goes to stdout - PROBLEM!
    
    # Processing logic...
    local result="ghcr.io/repo/image:tag"
    echo "$result"                      # Intended return value
}

# Usage captures ALL output, not just the intended result
IMAGE_TAG=$(extract_image_tag "$DOCKER_METADATA")
echo "Result: '$IMAGE_TAG'"
# Output: "Result: '🔧 Processing image tags...
# Input: metadata
# ghcr.io/repo/image:tag'"
```

### Solution: Proper Output Redirection

```bash
# ✅ CORRECT: Debug output goes to stderr, only result to stdout
extract_image_tag() {
    echo "🔧 Processing image tags..." >&2  # Debug to stderr
    echo "Input: $1" >&2                    # Debug to stderr
    
    # Processing logic...
    local result="ghcr.io/repo/image:tag"
    echo "$result"                          # Only result to stdout
}

# Usage captures only the intended result
IMAGE_TAG=$(extract_image_tag "$DOCKER_METADATA")
echo "Result: '$IMAGE_TAG'"
# Output: "Result: 'ghcr.io/repo/image:tag'"
# (Debug output visible on console but not captured)
```

### Advanced Examples

#### Complex Function with Multiple Debug Levels

```bash
validate_docker_image() {
    local image_metadata="$1"
    local debug_level="${DEBUG_LEVEL:-1}"
    
    # Level 1: Basic progress
    [[ $debug_level -ge 1 ]] && echo "🔍 Validating Docker image..." >&2
    
    # Level 2: Detailed processing
    [[ $debug_level -ge 2 ]] && {
        echo "📋 Raw metadata:" >&2
        echo "$image_metadata" | head -3 >&2
    }
    
    # Processing with error handling
    local selected_tag
    case "$GITHUB_EVENT_NAME" in
        "workflow_dispatch")
            selected_tag=$(echo "$image_metadata" | grep "sha-" | head -1)
            [[ $debug_level -ge 2 ]] && echo "🎯 Selected SHA tag: $selected_tag" >&2
            ;;
        "pull_request")
            selected_tag=$(echo "$image_metadata" | grep "pr-" | head -1)
            [[ $debug_level -ge 2 ]] && echo "🎯 Selected PR tag: $selected_tag" >&2
            ;;
        *)
            selected_tag=$(echo "$image_metadata" | head -1)
            [[ $debug_level -ge 2 ]] && echo "🎯 Selected default tag: $selected_tag" >&2
            ;;
    esac
    
    # Validation with error output to stderr
    if [[ -z "$selected_tag" ]]; then
        echo "❌ ERROR: No valid tag found" >&2
        echo "Available tags:" >&2
        echo "$image_metadata" >&2
        return 1
    fi
    
    # Format validation
    selected_tag=$(echo "$selected_tag" | tr -d '\n\r' | xargs)
    if [[ ! "$selected_tag" =~ ^[a-zA-Z0-9._/-]+:[a-zA-Z0-9._-]+$ ]]; then
        echo "❌ ERROR: Invalid tag format: '$selected_tag'" >&2
        return 1
    fi
    
    [[ $debug_level -ge 1 ]] && echo "✅ Validation successful" >&2
    
    # ONLY the validated tag goes to stdout
    echo "$selected_tag"
}

# Usage with different debug levels
DEBUG_LEVEL=1 IMAGE_TAG=$(validate_docker_image "$METADATA")  # Basic debug
DEBUG_LEVEL=2 IMAGE_TAG=$(validate_docker_image "$METADATA")  # Detailed debug
```

#### Function with Multiple Return Values

```bash
parse_version_info() {
    local version_string="$1"
    
    echo "🔧 Parsing version: $version_string" >&2
    
    # Extract components
    local major minor patch
    if [[ "$version_string" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
        major="${BASH_REMATCH[1]}"
        minor="${BASH_REMATCH[2]}"  
        patch="${BASH_REMATCH[3]}"
        
        echo "✅ Parsed: major=$major, minor=$minor, patch=$patch" >&2
        
        # Return structured data (only this goes to stdout)
        echo "$major|$minor|$patch"
    else
        echo "❌ ERROR: Invalid version format: $version_string" >&2
        return 1
    fi
}

# Usage with structured return
if version_info=$(parse_version_info "1.2.3"); then
    IFS='|' read -r major minor patch <<< "$version_info"
    echo "Major: $major, Minor: $minor, Patch: $patch"
fi
```

### Testing Output Redirection

```bash
# Test script to verify output redirection works correctly
test_function_output() {
    echo "Testing bash function output redirection..."
    
    # Capture only stdout (function result)
    result=$(extract_image_tag "test-metadata")
    echo "Captured result: '$result'"
    
    # Capture stderr (debug output) for verification
    debug_output=$(extract_image_tag "test-metadata" 2>&1 >/dev/null)
    echo "Debug output present: $([[ -n "$debug_output" ]] && echo "YES" || echo "NO")"
    
    # Test error conditions
    if ! error_result=$(failing_function 2>/dev/null); then
        echo "Error handling works correctly"
    fi
}
```

### Common Pitfalls and Solutions

#### Pitfall 1: Forgetting stderr redirection
```bash
# ❌ WRONG
echo "Debug message"
# ✅ CORRECT  
echo "Debug message" >&2
```

#### Pitfall 2: Mixing echo and printf
```bash
# ❌ INCONSISTENT
echo "Debug" >&2
printf "Result: %s" "$value"

# ✅ CONSISTENT
echo "Debug" >&2
echo "Result: $value"
```

#### Pitfall 3: Complex expressions in command substitution
```bash
# ❌ HARD TO DEBUG
result=$(complex_function "$input" | process_output | filter_result)

# ✅ EASIER TO DEBUG
temp_output=$(complex_function "$input")
processed=$(echo "$temp_output" | process_output)
result=$(echo "$processed" | filter_result)
```

This detailed guide provides comprehensive examples for implementing proper bash function output handling to prevent recurring debug output pollution issues.