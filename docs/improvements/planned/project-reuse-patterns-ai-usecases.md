# AI/MCP Reuse Patterns for Internal and External Users

This document outlines potential use cases for an AI or Multi-Copilot Platform (MCP) assistant for both internal contributors to the `mpo-api-authn-server` project and external customers who consume its client libraries.

---

## 1. Use Cases for Internal Contributors

For developers actively working on this repository, an AI assistant can streamline development, testing, and maintenance by deeply understanding the project's structure and conventions.

### Onboarding and Setup

An AI can act as an interactive guide for new contributors.

* **Task**: A new developer needs to set up their local development environment.
* **AI Action**: The AI would parse the `README.md`, `docs/setup/` guides, and `scripts/setup/` scripts. It would provide step-by-step instructions to:
    1. Install prerequisites (JDK, Node.js, Docker).
    2. Run the setup scripts (e.g., `setup-dev-tools.sh`).
    3. Start the necessary services using `docker-compose.yml` and `start-dev.sh`.
    4. Build the project with Gradle (`./gradlew build`).

### Code Development and Modification

The AI can accelerate development by automating repetitive tasks based on established patterns.

* **Task**: A developer needs to add a new API endpoint (e.g., for passwordless session renewal).
* **AI Action**: The AI would identify the project's API-driven workflow:
    1. Guide the developer to update the OpenAPI specification at `android-client-library/api/openapi.yaml`.
    2. Automatically re-run the Gradle task that generates client libraries (`android-client-library`, `typescript-client-library`) from the updated spec.
    3. Create skeleton handler functions in the `webauthn-server` Kotlin codebase, matching the new endpoint definition.
    4. Suggest creating corresponding tests in the `web-test-client` and `android-test-client`.

### Testing and Debugging

The AI can simplify the execution and analysis of tests.

* **Task**: A developer has made changes to the authentication logic and needs to run relevant tests.
* **AI Action**: The AI would identify the various test suites and run the appropriate commands:
    * Execute backend unit tests via `./gradlew :webauthn-server:test`.
    * Launch the Playwright end-to-end tests in `web-test-client`.
    * If a test fails, the AI can analyze `server.log`, test output, and the recent code changes to suggest potential root causes.

---

## 2. Use Cases for External Customers

For external developers who want to integrate the project's client libraries into their own applications, the AI's primary role is to provide secure, reliable, and easy-to-understand guidance.

### Secure Dependency Integration

This is the most critical security-focused use case. The AI acts as a verification engine to prevent supply chain attacks.

* **Task**: An external developer wants to add the TypeScript client to their web application.
* **AI Action**: The AI follows a zero-trust verification process:
    1. **Establish Root of Trust**: The developer provides a trusted identifier, such as the project's official GitHub URL (`https://github.com/hitoshura25/mpo-api-authn-server`).
    2. **Fetch Policy**: The AI retrieves a (hypothetical) `project-manifest.json` from this trusted URL to find the official npm package name.
    3. **Verify Signature**: The AI finds the package on npm and cryptographically verifies its Sigstore signature. It confirms that the package was signed by the CI/CD workflow originating from the trusted GitHub repository.
    4. **Provide Command**: Only after successful verification does the AI provide the safe `npm install` command to the user.

### Usage and Implementation Guidance

The AI acts as interactive, context-aware documentation.

* **Task**: The developer needs to implement the WebAuthn registration flow in their application.
* **AI Action**: The AI would:
    1. Reference the generated client documentation (e.g., `docs/RegistrationApi.md`).
    2. Provide code snippets in TypeScript showing the correct sequence of API calls (e.g., calling the registration start and finish endpoints).
    3. Explain the data models involved, using information from files like `RegistrationCompleteRequest.md`.

### Troubleshooting

The AI helps developers resolve common integration issues.

* **Task**: The developer's integration is failing with a specific error message.
* **AI Action**: The AI would reference the `ErrorResponse.md` documentation and the server's source code to explain what the error means and suggest common causes, such as an incorrect server URL configuration or a malformed request.
