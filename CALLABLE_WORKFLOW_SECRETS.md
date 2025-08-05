# GitHub Actions Callable Workflow Secrets Best Practices

## Overview

This document provides comprehensive guidance on handling secrets in GitHub Actions callable workflows, specifically addressing common pitfalls and best practices for secret propagation. This guidance was developed after resolving an npm publishing failure where the `npm_publish_token` secret wasn't properly propagated to callable workflows.

## Table of Contents

1. [Understanding Callable Workflow Secrets](#understanding-callable-workflow-secrets)
2. [The npm_publish_token Issue We Encountered](#the-npm_publish_token-issue-we-encountered)
3. [Best Practices for Secret Handling](#best-practices-for-secret-handling)
4. [Practical Examples](#practical-examples)
5. [Security Considerations](#security-considerations)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Testing and Validation](#testing-and-validation)

## Understanding Callable Workflow Secrets

### How Secrets Work in Callable Workflows

Unlike regular workflows, callable workflows (reusable workflows) have specific requirements for secret access:

1. **Explicit Declaration Required**: Callable workflows must explicitly declare secrets as inputs
2. **No Automatic Inheritance**: Secrets from the calling repository are NOT automatically available
3. **Must Be Passed Through**: The calling workflow must explicitly pass secrets to the callable workflow

### Key Differences from Regular Workflows

| Aspect | Regular Workflow | Callable Workflow |
|--------|------------------|-------------------|
| Secret Access | Automatic via `secrets.SECRET_NAME` | Must be declared as input |
| Declaration | Not required | Required in `on.workflow_call.secrets` |
| Propagation | N/A | Must be explicitly passed by caller |
| Scope | Repository secrets available | Only passed secrets available |

## The npm_publish_token Issue We Encountered

### Problem Description

Our workflow was failing during npm package publishing with authentication errors because the `npm_publish_token` secret wasn't being properly propagated from the calling workflows to the callable workflow.

### Root Cause

The callable workflow `client-e2e-tests.yml` was attempting to use `secrets.npm_publish_token` without:
1. Declaring it as a required secret input
2. Having it passed from the calling workflows

### Before (Incorrect Configuration)

**Callable Workflow** (`client-e2e-tests.yml`):
```yaml
name: Client E2E Tests
on:
  workflow_call:
    # Missing secrets declaration
    inputs:
      # ... other inputs

jobs:
  test:
    steps:
      - name: Setup npm authentication
        run: |
          # This would fail - secret not available
          echo "//registry.npmjs.org/:_authToken=${{ secrets.npm_publish_token }}" >> ~/.npmrc
```

**Calling Workflow** (`pull-request.yml`):
```yaml
jobs:
  client-tests:
    uses: ./.github/workflows/client-e2e-tests.yml
    # Missing secrets propagation
    with:
      # ... inputs only
```

### After (Correct Configuration)

**Callable Workflow** (`client-e2e-tests.yml`):
```yaml
name: Client E2E Tests
on:
  workflow_call:
    secrets:
      npm_publish_token:
        description: 'NPM publish token for package authentication'
        required: true
    inputs:
      # ... other inputs

jobs:
  test:
    steps:
      - name: Setup npm authentication
        run: |
          # Now works correctly
          echo "//registry.npmjs.org/:_authToken=${{ secrets.npm_publish_token }}" >> ~/.npmrc
```

**Calling Workflow** (`pull-request.yml`):
```yaml
jobs:
  client-tests:
    uses: ./.github/workflows/client-e2e-tests.yml
    secrets:
      npm_publish_token: ${{ secrets.NPM_PUBLISH_TOKEN }}
    with:
      # ... other inputs
```

## Best Practices for Secret Handling

### 1. Always Declare Secrets Explicitly

```yaml
on:
  workflow_call:
    secrets:
      secret_name:
        description: 'Clear description of what this secret is used for'
        required: true  # or false if optional
```

### 2. Use Descriptive Secret Names

**Good**:
```yaml
secrets:
  npm_publish_token:
    description: 'NPM registry authentication token'
  docker_registry_password:
    description: 'Docker Hub registry password'
  github_packages_token:
    description: 'GitHub Packages authentication token'
```

**Bad**:
```yaml
secrets:
  token:
    description: 'Token'
  password:
    description: 'Password'
```

### 3. Document Secret Requirements

Always include documentation about:
- What secrets are required
- Where to obtain them
- How they should be configured
- What permissions they need

### 4. Use Consistent Naming Conventions

- Repository secrets: `UPPER_SNAKE_CASE` (e.g., `NPM_PUBLISH_TOKEN`)
- Workflow inputs: `lower_snake_case` (e.g., `npm_publish_token`)
- Environment variables: `UPPER_SNAKE_CASE` (e.g., `NPM_TOKEN`)

### 5. Minimize Secret Exposure

Only pass secrets that are actually needed:

```yaml
# Good - only necessary secrets
secrets:
  npm_publish_token: ${{ secrets.NPM_PUBLISH_TOKEN }}

# Bad - passing all secrets unnecessarily
secrets: inherit
```

## Practical Examples

### Example 1: NPM Package Publishing

**Callable Workflow** (`publish-npm-package.yml`):
```yaml
name: Publish NPM Package
on:
  workflow_call:
    secrets:
      npm_publish_token:
        description: 'NPM registry authentication token with publish permissions'
        required: true
      github_token:
        description: 'GitHub token for repository access'
        required: false
    inputs:
      package_path:
        description: 'Path to the package to publish'
        required: true
        type: string
      registry_url:
        description: 'NPM registry URL'
        required: false
        type: string
        default: 'https://registry.npmjs.org'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.github_token || github.token }}
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          registry-url: ${{ inputs.registry_url }}
      
      - name: Configure npm authentication
        run: |
          echo "//${{ inputs.registry_url }}/:_authToken=${{ secrets.npm_publish_token }}" >> ~/.npmrc
        env:
          NODE_AUTH_TOKEN: ${{ secrets.npm_publish_token }}
      
      - name: Install dependencies
        run: npm ci
        working-directory: ${{ inputs.package_path }}
      
      - name: Build package
        run: npm run build
        working-directory: ${{ inputs.package_path }}
      
      - name: Publish package
        run: npm publish
        working-directory: ${{ inputs.package_path }}
```

**Calling Workflow** (`release.yml`):
```yaml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  publish-client-library:
    uses: ./.github/workflows/publish-npm-package.yml
    secrets:
      npm_publish_token: ${{ secrets.NPM_PUBLISH_TOKEN }}
      github_token: ${{ secrets.GITHUB_TOKEN }}
    with:
      package_path: './generated-client-library'
      registry_url: 'https://registry.npmjs.org'
```

### Example 2: Docker Registry Authentication

**Callable Workflow** (`docker-build-push.yml`):
```yaml
name: Docker Build and Push
on:
  workflow_call:
    secrets:
      docker_username:
        description: 'Docker registry username'
        required: true
      docker_password:
        description: 'Docker registry password or token'
        required: true
    inputs:
      image_name:
        description: 'Docker image name'
        required: true
        type: string
      registry:
        description: 'Docker registry URL'
        required: false
        type: string
        default: 'docker.io'

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Log in to Docker Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ inputs.registry }}
          username: ${{ secrets.docker_username }}
          password: ${{ secrets.docker_password }}
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ inputs.registry }}/${{ inputs.image_name }}:latest
```

### Example 3: Multiple Authentication Methods

**Callable Workflow** (`multi-auth-workflow.yml`):
```yaml
name: Multi-Authentication Workflow
on:
  workflow_call:
    secrets:
      # NPM authentication
      npm_token:
        description: 'NPM registry token'
        required: true
      # GitHub Packages authentication
      github_packages_token:
        description: 'GitHub Packages token'
        required: false
      # AWS authentication
      aws_access_key_id:
        description: 'AWS Access Key ID'
        required: false
      aws_secret_access_key:
        description: 'AWS Secret Access Key'
        required: false
    inputs:
      enable_aws:
        description: 'Enable AWS operations'
        required: false
        type: boolean
        default: false

jobs:
  multi-auth-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup NPM authentication
        run: |
          echo "//registry.npmjs.org/:_authToken=${{ secrets.npm_token }}" >> ~/.npmrc
      
      - name: Setup GitHub Packages authentication
        if: secrets.github_packages_token
        run: |
          echo "//npm.pkg.github.com/:_authToken=${{ secrets.github_packages_token }}" >> ~/.npmrc
      
      - name: Configure AWS credentials
        if: inputs.enable_aws && secrets.aws_access_key_id && secrets.aws_secret_access_key
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.aws_access_key_id }}
          aws-secret-access-key: ${{ secrets.aws_secret_access_key }}
          aws-region: us-east-1
```

## Security Considerations

### 1. Principle of Least Privilege

Only pass secrets that are absolutely necessary for the workflow to function:

```yaml
# Good - minimal secret exposure
secrets:
  npm_token: ${{ secrets.NPM_PUBLISH_TOKEN }}

# Avoid - exposes all repository secrets
secrets: inherit
```

### 2. Secret Validation

Validate that required secrets are present before using them:

```yaml
steps:
  - name: Validate required secrets
    run: |
      if [ -z "${{ secrets.npm_publish_token }}" ]; then
        echo "Error: npm_publish_token is required but not provided"
        exit 1
      fi
```

### 3. Secure Secret Usage

Use secrets in environment variables rather than command line arguments:

```yaml
# Good - secret in environment variable
- name: Authenticate with npm
  run: npm config set //registry.npmjs.org/:_authToken $NPM_TOKEN
  env:
    NPM_TOKEN: ${{ secrets.npm_publish_token }}

# Bad - secret in command line (visible in logs)
- name: Authenticate with npm
  run: npm config set //registry.npmjs.org/:_authToken ${{ secrets.npm_publish_token }}
```

### 4. Conditional Secret Usage

Use conditions to avoid exposing secrets unnecessarily:

```yaml
steps:
  - name: Setup authentication
    if: secrets.npm_publish_token != ''
    run: |
      echo "//registry.npmjs.org/:_authToken=${{ secrets.npm_publish_token }}" >> ~/.npmrc
```

## Troubleshooting Guide

### Common Error Messages and Solutions

#### 1. "Secret not found" or "Undefined secret"

**Error**: Workflow fails with messages like:
- `secret 'npm_publish_token' not found`
- `undefined secret reference`

**Cause**: Secret not declared in callable workflow or not passed by caller.

**Solution**:
1. Add secret declaration to callable workflow:
   ```yaml
   on:
     workflow_call:
       secrets:
         npm_publish_token:
           required: true
   ```

2. Pass secret from calling workflow:
   ```yaml
   secrets:
     npm_publish_token: ${{ secrets.NPM_PUBLISH_TOKEN }}
   ```

#### 2. Authentication Failures

**Error**: Authentication fails during npm publish, Docker push, etc.

**Cause**: Secret value is empty, incorrect, or expired.

**Solution**:
1. Verify secret exists in repository settings
2. Check secret value is correct and not expired
3. Validate secret has necessary permissions
4. Test secret outside of GitHub Actions if possible

#### 3. "secrets: inherit not allowed"

**Error**: Using `secrets: inherit` in certain contexts.

**Cause**: `secrets: inherit` is not supported in all workflow types.

**Solution**: Explicitly pass required secrets:
```yaml
secrets:
  npm_token: ${{ secrets.NPM_PUBLISH_TOKEN }}
  docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

### Debugging Steps

#### 1. Verify Secret Declaration

Check that secrets are properly declared in the callable workflow:

```bash
# Check workflow file for secret declarations
grep -A 10 "secrets:" .github/workflows/your-callable-workflow.yml
```

#### 2. Verify Secret Propagation

Check that secrets are being passed from calling workflows:

```bash
# Check calling workflow for secret passing
grep -A 5 "secrets:" .github/workflows/your-calling-workflow.yml
```

#### 3. Test Secret Access

Add a debug step to verify secret is available (be careful not to expose actual secret):

```yaml
- name: Debug secret availability
  run: |
    if [ -n "${{ secrets.your_secret }}" ]; then
      echo "Secret is available"
    else
      echo "Secret is not available"
      exit 1
    fi
```

#### 4. Check Repository Settings

Verify secrets are configured in repository settings:
1. Go to Settings → Secrets and variables → Actions
2. Verify required secrets exist
3. Check secret names match exactly (case-sensitive)

### Validation Checklist

Before deploying workflows with secrets:

- [ ] All required secrets declared in callable workflow
- [ ] Secrets passed from all calling workflows
- [ ] Secret names match between declaration and usage
- [ ] Repository secrets exist and are correctly named
- [ ] Secrets have necessary permissions for their intended use
- [ ] No secrets exposed in logs or command lines
- [ ] Conditional logic handles missing optional secrets
- [ ] Documentation updated with secret requirements

## Testing and Validation

### 1. Local Testing

While you can't test actual secrets locally, you can validate workflow syntax:

```bash
# Install act for local GitHub Actions testing
# Note: Secrets won't work locally, but syntax can be validated
act --list
```

### 2. Workflow Validation

Use GitHub's workflow validation:

```yaml
name: Validate Workflow
on:
  pull_request:
    paths:
      - '.github/workflows/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate workflow files
        run: |
          # Check for common issues
          grep -r "secrets\." .github/workflows/ || echo "No direct secret usage found"
          # Add more validation as needed
```

### 3. Secret Availability Tests

Add tests to verify secrets are properly configured:

```yaml
jobs:
  test-secrets:
    runs-on: ubuntu-latest
    steps:
      - name: Test secret availability
        run: |
          secrets_missing=0
          
          if [ -z "${{ secrets.npm_publish_token }}" ]; then
            echo "❌ npm_publish_token is missing"
            secrets_missing=1
          else
            echo "✅ npm_publish_token is available"
          fi
          
          if [ $secrets_missing -eq 1 ]; then
            echo "Some required secrets are missing"
            exit 1
          fi
          
          echo "All required secrets are available"
```

## Conclusion

Proper secret handling in callable workflows requires:

1. **Explicit Declaration**: All secrets must be declared as inputs
2. **Proper Propagation**: Calling workflows must pass secrets explicitly
3. **Security Awareness**: Follow principle of least privilege
4. **Testing**: Validate secret availability and workflow syntax
5. **Documentation**: Keep secret requirements well-documented

By following these best practices, you can avoid the authentication failures we encountered and ensure secure, reliable workflow execution.

## Additional Resources

- [GitHub Actions: Reusing workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [GitHub Actions: Using secrets in GitHub Actions](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [GitHub Actions: Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)