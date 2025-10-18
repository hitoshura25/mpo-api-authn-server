import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname, resolve, relative, isAbsolute, sep } from 'path';
import { fileURLToPath } from 'url';
import Handlebars from 'handlebars';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Validates that a user-provided path is safe and contained within a base directory.
 * Implements industry-standard path traversal prevention with multiple validation layers.
 *
 * Security Approach:
 * 1. Pre-Resolution Validation: Sanitize and validate input BEFORE path.resolve()
 * 2. Post-Resolution Containment: Verify resolved path stays within base directory
 * 3. Defense in Depth: Multiple independent checks for maximum security
 *
 * @param basePath - The base directory that should contain the result
 * @param userPath - The user-provided path (potentially malicious)
 * @returns The validated absolute path
 * @throws Error if path traversal is detected
 *
 * @see https://github.com/googleapis/nodejs-storage/pull/2654
 * @see https://owasp.org/www-community/attacks/Path_Traversal
 */
function validatePathContainment(basePath: string, userPath: string): string {
  // ========================================
  // PRE-RESOLUTION VALIDATION
  // Validate input BEFORE calling path.resolve()
  // ========================================

  // 1. URL decode to prevent encoding-based bypass attacks
  //    Example: %2e%2e%2f%2e%2e%2f encodes ../../
  let decodedPath: string;
  try {
    decodedPath = decodeURIComponent(userPath);
  } catch (error) {
    // Invalid URI encoding - likely malicious
    throw new Error(
      `Path traversal detected: Invalid URI encoding in path '${userPath}'`
    );
  }

  // 2. Reject absolute paths immediately (before path.resolve)
  //    Example: /etc/passwd, C:\Windows\System32
  if (isAbsolute(decodedPath)) {
    throw new Error(
      `Path traversal detected: Absolute paths not allowed.\n` +
      `Received: '${userPath}'\n` +
      `Decoded: '${decodedPath}'`
    );
  }

  // 3. Early detection of obvious traversal markers (defense in depth)
  //    Note: Main defense is post-resolution check, but this provides early warning
  if (decodedPath.includes('..')) {
    // Don't reject yet - path.relative() check is authoritative
    // But log for security monitoring
    console.warn(
      `[Security] Path contains '..' marker: ${userPath} (will validate post-resolution)`
    );
  }

  // ========================================
  // RESOLUTION
  // Now safe to call path.resolve() with pre-validated input
  // ========================================

  const resolvedBase = resolve(basePath);
  const resolvedPath = resolve(basePath, decodedPath);

  // ========================================
  // POST-RESOLUTION CONTAINMENT CHECKS
  // Verify resolved path stays within base directory
  // ========================================

  // 4. PRIMARY CHECK: Use path.relative() to detect directory escape
  //    Industry standard pattern (Google Cloud, enterprise security)
  //    Example:
  //      relative('/base', '/base/sub')    → 'sub'       ✅ Safe
  //      relative('/base', '/etc/passwd')  → '../../etc' ❌ Escaped
  const relativePath = relative(resolvedBase, resolvedPath);

  if (relativePath.startsWith('..') || isAbsolute(relativePath)) {
    throw new Error(
      `Path traversal detected: '${userPath}' resolves outside allowed directory.\n` +
      `Base directory: ${resolvedBase}\n` +
      `Attempted path: ${resolvedPath}\n` +
      `Relative path: ${relativePath}\n` +
      `Reason: ${relativePath.startsWith('..') ? 'Escapes base with ..' : 'Results in absolute path'}`
    );
  }

  // 5. SECONDARY CHECK: Prefix validation with path separator (defense in depth)
  //    Prevents false matches with similar directory names
  //    Example: /var/www should not match /var/www-backup
  const normalizedBase = resolvedBase + sep;
  const normalizedPath = resolvedPath + sep;

  if (!normalizedPath.startsWith(normalizedBase) && resolvedPath !== resolvedBase) {
    throw new Error(
      `Path traversal detected: Resolved path does not start with base directory.\n` +
      `Base directory: ${resolvedBase}\n` +
      `Resolved path: ${resolvedPath}\n` +
      `Normalized base: ${normalizedBase}\n` +
      `Normalized path: ${normalizedPath}`
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
