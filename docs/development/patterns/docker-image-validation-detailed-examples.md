# Docker Image Validation - Detailed Examples

**Extracted from CLAUDE.md for detailed reference**  
**Core pattern remains in CLAUDE.md**

## Comprehensive Docker Image Validation Implementation

### Multi-line Docker Tag Handling Examples

```bash
# Extract image tag function with full error handling
extract_image_tag() {
  local image_type="$1"
  local full_output
  full_output=$(cat)
  
  echo "🔧 Processing $image_type image tags:" >&2
  echo "$full_output" | head -3 >&2
  
  local selected_tag
  case "${{ github.event_name }}" in
    "workflow_dispatch")
      # Use SHA-based tag for manual triggers
      selected_tag=$(echo "$full_output" | head -1 | grep "sha-" | head -1)
      if [[ -z "$selected_tag" ]]; then
        echo "❌ ERROR: No SHA-based tag found for workflow_dispatch" >&2
        echo "Available tags:" >&2
        echo "$full_output" | head -5 >&2
        return 1
      fi
      echo "🎯 Selected SHA tag for workflow_dispatch: $selected_tag" >&2
      ;;
    "pull_request")
      # Use PR tag for pull requests  
      selected_tag=$(echo "$full_output" | head -1 | grep "pr-" | head -1)
      if [[ -z "$selected_tag" ]]; then
        echo "❌ ERROR: No PR tag found for pull_request event" >&2
        return 1
      fi
      echo "🎯 Selected PR tag: $selected_tag" >&2
      ;;
    *)
      # Use first available tag
      selected_tag=$(echo "$full_output" | head -1)
      echo "🎯 Selected first available tag for ${{ github.event_name }}: $selected_tag" >&2
      ;;
  esac
  
  # Clean whitespace and validate format
  selected_tag=$(echo "$selected_tag" | tr -d '\n\r' | xargs)
  
  if [[ ! "$selected_tag" =~ ^[a-zA-Z0-9._/-]+:[a-zA-Z0-9._-]+$ ]]; then
    echo "❌ ERROR: Tag format validation failed: '$selected_tag'" >&2
    return 1
  fi
  
  echo "$selected_tag"  # Only this goes to stdout
}
```

### Complete Validation Workflow Example

```yaml
validate-images:
  name: Validate Docker Images
  runs-on: ubuntu-latest
  needs: [ build-push-docker-images ]
  if: always() && needs.build-push-docker-images.result == 'success'
  outputs:
    webauthn-server-ready: ${{ steps.validate-webauthn.outputs.ready }}
    test-credentials-ready: ${{ steps.validate-test-credentials.outputs.ready }}
  steps:
    - name: Validate WebAuthn Server Image
      id: validate-webauthn
      env:
        DOCKER_METADATA: ${{ needs.build-push-docker-images.outputs.webauthn_server_image }}
        EVENT_NAME: ${{ github.event_name }}
        BRANCH_NAME: ${{ github.ref_name }}
      run: |
        echo "🔍 Validating WebAuthn Server image availability..."
        echo "Event: $EVENT_NAME, Branch: $BRANCH_NAME"
        echo "Raw metadata: $DOCKER_METADATA"
        
        # Extract and validate tag
        WEBAUTHN_TAG=$(echo "$DOCKER_METADATA" | ./scripts/ci/extract_image_tag.sh "WebAuthn-Server")
        if [[ $? -ne 0 ]]; then
          echo "❌ WebAuthn Server tag extraction failed"
          exit 1
        fi
        
        echo "✅ WebAuthn Server tag validated: $WEBAUTHN_TAG"
        echo "ready=true" >> $GITHUB_OUTPUT
```

### Error Patterns and Solutions

#### Common Multi-line Tag Issues
1. **Newlines in tag strings**: Use `tr -d '\n\r'` and `xargs` for cleaning
2. **Empty tag selection**: Always validate extracted tags are non-empty
3. **Wrong event type selection**: Use `${{ github.event_name }}` for logic
4. **Format validation**: Use regex to ensure proper `image:tag` format

#### Debug Commands for Troubleshooting
```bash
# View raw Docker metadata output
echo "$DOCKER_METADATA" | head -5

# Test tag extraction locally  
echo "$DOCKER_METADATA" | ./scripts/ci/extract_image_tag.sh "WebAuthn-Server"

# Validate tag format
if [[ "$TAG" =~ ^[a-zA-Z0-9._/-]+:[a-zA-Z0-9._-]+$ ]]; then
  echo "✅ Valid format"
else
  echo "❌ Invalid format: $TAG"
fi
```

This detailed implementation guide supplements the essential pattern in CLAUDE.md with comprehensive examples for complex scenarios.