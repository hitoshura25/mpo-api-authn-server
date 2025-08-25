# Advanced Reuse: Templates and Scaffolding

This document details patterns for reusing the `mpo-api-authn-server` project structure, either as a simple template or through an advanced scaffolding tool.

---

## 1. GitHub Template Repository

A straightforward way to enable reuse is to mark this repository as a "Template" in its GitHub settings. This allows any user to generate a new repository with the exact same directory structure, files, and CI/CD workflows.

### Use Case

A developer wants to start a new secure service and likes the structure and security practices of `mpo-api-authn-server`.

### Workflow

1. The user navigates to `https://github.com/hitoshura25/mpo-api-authn-server`.
2. They click the "Use this template" button.
3. GitHub creates a new repository in their account with a complete copy of the code.

### Benefits

* **Simplicity**: No special tools required; it's a native GitHub feature.
* **Best Practices Included**: The new project automatically inherits the CI/CD pipeline, security scanning (Detekt, vulnerability checks), and documentation structure.
* **Immediate Start**: The developer gets a working, buildable skeleton project instantly.

### Limitations

* **Manual Renaming**: The user must manually find and replace all instances of `mpo-api-authn-server`, `hitoshura25`, and other project-specific names in files like `build.gradle.kts`, `settings.gradle.kts`, `package.json`, and workflow files. This is tedious and error-prone.

---

## 2. Advanced Scaffolding with Cookiecutter

For a more robust and user-friendly experience, the project can be converted into a Cookiecutter template. Cookiecutter is a command-line utility that creates projects from project templates, prompting the user for custom values.

### Use Case

A team wants to bootstrap a new microservice based on this project's architecture but needs to customize all names, package identifiers, and scopes from the very beginning.

### Implementation

1. **Create a Template**: A new repository, e.g., `mpo-api-authn-server-template`, would be created.
2. **Add Placeholders**: Project-specific names in files would be replaced with Cookiecutter variables.
    * In `settings.gradle.kts`: `rootProject.name = "{{ project_slug }}"`
    * In `typescript-client-library/package.json`: `"name": "@{{ npm_scope }}/{{ project_slug }}-client"`
    * In `.github/workflows/main-ci-cd.yml`: `repository: {{ github_user }}/{{ project_slug }}`
3. **Define Variables**: A `cookiecutter.json` file is added to the root of the template to define the variables the user will be prompted for.

   ```json
   {
     "project_name": "My Awesome Project",
     "project_slug": "{{ cookiecutter.project_name.lower().replace(' ', '-') }}",
     "github_user": "hitoshura25",
     "npm_scope": "my-npm-scope",
     "maven_group_id": "com.example"
   }
   ```

### Workflow

1. The user installs Cookiecutter (`pip install cookiecutter`).
2. They run the command: `cookiecutter gh:hitoshura25/mpo-api-authn-server-template`
3. Cookiecutter prompts them to enter values for `project_name`, `github_user`, etc.
4. A new, fully customized project directory is generated on their local machine, with all placeholders correctly filled in.

### Benefits

* **Automated Customization**: Eliminates the manual, error-prone process of finding and replacing names.
* **Reduced Setup Friction**: Provides a clean, ready-to-use project tailored to the user's needs.
* **Enforces Conventions**: Ensures that all new projects started from the template follow the desired naming and structural conventions.
