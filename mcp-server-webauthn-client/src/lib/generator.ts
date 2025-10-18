import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname, resolve, sep } from 'path';
import { fileURLToPath } from 'url';
import Handlebars from 'handlebars';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Validates that a resolved path is contained within a base directory.
 * Prevents path traversal attacks by ensuring the final path doesn't escape the base.
 *
 * @param basePath - The base directory that should contain the result
 * @param userPath - The user-provided path (potentially malicious)
 * @returns The validated absolute path
 * @throws Error if path traversal is detected
 */
function validatePathContainment(basePath: string, userPath: string): string {
  // Resolve both paths to absolute, normalized forms
  const resolvedBase = resolve(basePath);
  const resolvedPath = resolve(basePath, userPath);

  // Add path separator to base to prevent false matches with similar directory names
  // Example: /var/www should not match /var/www-backup
  const normalizedBase = resolvedBase + sep;
  const normalizedPath = resolvedPath + sep;

  // Verify the resolved path is within the base directory
  if (!normalizedPath.startsWith(normalizedBase) && resolvedPath !== resolvedBase) {
    throw new Error(
      `Path traversal detected: '${userPath}' resolves outside allowed directory. ` +
      `Resolved to: ${resolvedPath}, Expected within: ${resolvedBase}`
    );
  }

  return resolvedPath;
}

interface GenerateWebClientArgs {
  project_path: string;
  framework?: 'vanilla' | 'react' | 'vue';
  server_url?: string;
  client_port?: number;
}

export async function generateWebClient(args: GenerateWebClientArgs) {
  const {
    project_path,
    framework = 'vanilla',
    server_url = 'http://localhost:8080',
    client_port = 8082
  } = args;

  // Validate framework against whitelist
  if (!['vanilla', 'react', 'vue'].includes(framework)) {
    throw new Error(`Unsupported framework: ${framework}. Use 'vanilla', 'react', or 'vue'.`);
  }

  // Security: Validate project_path to prevent path traversal attacks
  // Get current working directory as the base for allowed operations
  const cwd = process.cwd();
  let validatedProjectPath: string;

  try {
    // Validate that project_path resolves within current working directory
    validatedProjectPath = validatePathContainment(cwd, project_path);
  } catch (error: any) {
    throw new Error(
      `Invalid project path: ${error.message}\n` +
      `Path must be relative to current directory and cannot contain '..' traversals.`
    );
  }

  // Check if directory exists (using validated path)
  if (existsSync(validatedProjectPath)) {
    throw new Error(`Directory already exists: ${project_path}. Please choose a different path or remove the existing directory.`);
  }

  const files_created: string[] = [];

  // Security: Validate framework path to prevent traversal in template directory
  const templatesBase = join(__dirname, '..', 'templates');
  const template_dir = validatePathContainment(templatesBase, framework);

  // Template files to generate
  const template_files = [
    { template: 'package.json.hbs', output: 'package.json' },
    { template: 'index.ts.hbs', output: 'src/index.ts' },
    { template: 'webauthn-client.ts.hbs', output: 'src/webauthn-client.ts' },
    { template: 'types.ts.hbs', output: 'src/types.ts' },
    { template: 'server.ts.hbs', output: 'src/server.ts' },
    { template: 'index.html.hbs', output: 'public/index.html' },
    { template: 'webpack.config.js.hbs', output: 'webpack.config.js' },
    { template: 'tsconfig.json.hbs', output: 'tsconfig.json' },
    { template: 'tsconfig.build.json.hbs', output: 'tsconfig.build.json' },
    { template: 'README.md.hbs', output: 'README.md' }
  ];

  // Template variables
  const template_vars = {
    server_url,
    client_port
  };

  try {
    // Create project directory structure (using validated path)
    mkdirSync(validatedProjectPath, { recursive: true });
    mkdirSync(join(validatedProjectPath, 'src'), { recursive: true });
    mkdirSync(join(validatedProjectPath, 'public'), { recursive: true });

    // Generate files from templates
    for (const { template, output } of template_files) {
      const template_path = join(template_dir, template);

      // Security: Validate output path stays within project directory
      const output_path = validatePathContainment(validatedProjectPath, output);

      // Read template
      const template_content = readFileSync(template_path, 'utf8');

      // Compile and render template
      const compiled_template = Handlebars.compile(template_content);
      const rendered_content = compiled_template(template_vars);

      // Ensure output directory exists
      mkdirSync(dirname(output_path), { recursive: true });

      // Write file
      writeFileSync(output_path, rendered_content, 'utf8');
      files_created.push(output_path);
    }

    return {
      content: [
        {
          type: 'text',
          text: `✅ Web client generated successfully!\n\nFiles created:\n${files_created.map(f => `  - ${f}`).join('\n')}\n\nNext steps:\n1. cd ${project_path}\n2. npm install\n3. npm run build\n4. npm start\n5. Open http://localhost:${client_port}`,
        },
      ],
    };
  } catch (error: any) {
    return {
      content: [
        {
          type: 'text',
          text: `Error generating web client: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}
