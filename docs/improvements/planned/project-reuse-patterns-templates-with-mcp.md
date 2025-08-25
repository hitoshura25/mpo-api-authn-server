# AI-Aware Blueprints: Combining Project Templates with a Model Context Protocol (MCP)

This document outlines a powerful pattern for AI-assisted software development that combines a foundational project template with a Model Context Protocol (MCP). This approach turns a static template into a dynamic, AI-aware blueprint, enabling an AI assistant to intelligently build upon your established architectural patterns.

---

## The Core Concept

The system is composed of three distinct components working together:

1. **The Foundational Project Template**: Provides the *structure*. This is a repository containing the skeleton of a project, including directory layouts, CI/CD workflow files (like `.github/workflows/build-and-test.yml`), configuration files (`config/publishing-config.yml`), and boilerplate code. It defines *what* a good project looks like.

2. **The AI Assistant**: Provides the *implementation*. This is the generative agent (e.g., GitHub Copilot, Claude) that writes the business logic, API specifications, and other project-specific code based on user prompts.

3. **The Model Context Protocol (MCP)**: Acts as the *live API* between the template and the AI. It's a script or tool included in the template that allows the AI to programmatically query the project's structure, conventions, and build processes. It answers the AI's question, "How do I do things in *this* project?"

---

## Example Workflow: Building a New Service with an MCP-Aware AI

Imagine you have created a foundational template from the `mpo-api-authn-server` project. This template includes a generic MCP provider script.

**Goal**: Create a new "Podcast Service".

1. **Scaffolding**: You generate a new project from the template. It creates a `podcast-api` directory with the standard structure and the MCP script.

2. **Prompt**: You tell your AI, "Define an OpenAPI spec for a podcast service."

3. **AI-MCP Interaction**:
    * **AI Asks**: `get_openapi_spec_path()`
    * **MCP Responds**: The MCP script reads the project structure and determines the conventional location. It returns: `{"path": "podcast-server/src/main/resources/openapi.yaml"}`.
    * **AI Acts**: The AI creates the spec file in the correct location without needing further instruction.

4. **Prompt**: "Generate a webservice that implements the spec using Kotlin and Spring."

5. **AI-MCP Interaction**:
    * **AI Asks**: `get_server_source_root()` and `get_build_command()`.
    * **MCP Responds**: `{"path": "podcast-server/src/main/kotlin"}` and `{"command": "./gradlew build"}`.
    * **AI Acts**: The AI generates the Kotlin source files in the correct directory.

6. **Prompt**: "Now, generate a TypeScript client library."

7. **AI-MCP Interaction**:
    * **AI Asks**: `get_client_generation_info()`.
    * **MCP Responds**: `{"command": "./gradlew openApiGenerate", "output_dir_pattern": "<language>-client"}`.
    * **AI Acts**: The AI knows the exact Gradle task to run and the directory naming convention to use for the new `typescript-client` directory.

8. **Prompt**: "Update the CI pipeline to test the new client."

9. **AI-MCP Interaction**:
    * **AI Asks**: `get_ci_workflow_paths()`.
    * **MCP Responds**: `{"main": ".github/workflows/main-ci-cd.yml", "build_and_test": ".github/workflows/build-and-test.yml"}`.
    * **AI Acts**: The AI reads the existing callable workflows and intelligently adds a new job or step for the TypeScript client tests, perfectly matching the established patterns in the YAML files.

---

## Key Benefits

* **Reduces Manual Guidance**: The developer focuses on high-level goals ("what to build") instead of low-level instructions ("where to put files").
* **Increases AI Accuracy**: The AI operates on structured, reliable data from the MCP, eliminating errors that arise from guessing paths or misinterpreting file names.
* **Codifies Architectural Patterns**: The MCP becomes the executable documentation for your project's conventions. It programmatically enforces standards for both human and AI contributors.
* **Evolves with Your Project**: When you update a pattern in your template (e.g., change a build command or a configuration file location), you update the MCP script once. Every subsequent use of the template by the AI will automatically adhere to the new standard.
