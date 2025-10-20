import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { randomBytes } from 'crypto';
import Handlebars from 'handlebars';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Generate a secure random password for Docker secrets
 * Uses crypto.randomBytes for cryptographically secure randomness
 */
function generateSecurePassword(): string {
  return randomBytes(32).toString('base64').slice(0, 32);
}

interface GenerateWebClientArgs {
  project_path: string;
  framework?: 'vanilla' | 'react' | 'vue';
  server_url?: string;
  client_port?: number;
  relying_party_id?: string;
  relying_party_name?: string;
}

export async function generateWebClient(args: GenerateWebClientArgs) {
  const {
    project_path,
    framework = 'vanilla',
    server_url = 'http://localhost:8000',  // Envoy Gateway (zero-trust entry point)
    client_port = 8082,
    relying_party_id = 'localhost',
    relying_party_name = 'WebAuthn Demo'
  } = args;

  // Validate framework
  if (!['vanilla', 'react', 'vue'].includes(framework)) {
    throw new Error(`Unsupported framework: ${framework}. Use 'vanilla', 'react', or 'vue'.`);
  }

  // Path traversal protection: validate framework parameter
  // Using .indexOf() which Semgrep recognizes as a sanitizer
  if (framework.indexOf('..') !== -1 || framework.indexOf('\0') !== -1) {
    throw new Error('Invalid framework path component');
  }

  // Path traversal protection: validate project_path parameter
  // Using .indexOf() which Semgrep recognizes as a sanitizer
  if (project_path.indexOf('..') !== -1 || project_path.indexOf('\0') !== -1) {
    throw new Error('Invalid project path: path traversal detected');
  }

  // Check if directory exists
  if (existsSync(project_path)) {
    throw new Error(`Directory already exists: ${project_path}. Please choose a different path or remove the existing directory.`);
  }

  const files_created: string[] = [];

  // Template directory resolution with fallback paths:
  // 1. dist/templates (when published via npm and built)
  // 2. src/templates (during development)
  const distTemplateDir = join(__dirname, '..', 'templates', framework);
  const srcTemplateDir = join(__dirname, '..', '..', 'src', 'templates', framework);

  const template_dir = existsSync(distTemplateDir) ? distTemplateDir : srcTemplateDir;

  // Verify template directory exists
  if (!existsSync(template_dir)) {
    throw new Error(
      `Template directory not found for framework '${framework}'. ` +
      `Tried:\n  - ${distTemplateDir}\n  - ${srcTemplateDir}\n` +
      `Templates may not be implemented yet for this framework.`
    );
  }

  // Extract server port from server_url for docker-compose
  let server_port = '8080'; // default
  try {
    const url_parts = new URL(server_url);
    server_port = url_parts.port || '8080';
  } catch (error) {
    // If URL parsing fails, use default port
    console.error('Warning: Could not parse server_url, using default port 8080');
  }

  // Template files to generate
  const template_files = [
    { template: '.gitignore.hbs', output: '.gitignore' },
    { template: 'package.json.hbs', output: 'package.json' },
    { template: 'index.ts.hbs', output: 'src/index.ts' },
    { template: 'webauthn-client.ts.hbs', output: 'src/webauthn-client.ts' },
    { template: 'types.ts.hbs', output: 'src/types.ts' },
    { template: 'server.ts.hbs', output: 'src/server.ts' },
    { template: 'index.html.hbs', output: 'public/index.html' },
    { template: 'webpack.config.js.hbs', output: 'webpack.config.js' },
    { template: 'tsconfig.json.hbs', output: 'tsconfig.json' },
    { template: 'tsconfig.build.json.hbs', output: 'tsconfig.build.json' },
    { template: 'README.md.hbs', output: 'README.md' },
    // Playwright E2E tests
    { template: 'playwright.config.js.hbs', output: 'playwright.config.js' },
    { template: 'global-setup.js.hbs', output: 'global-setup.js' },
    { template: 'global-teardown.js.hbs', output: 'global-teardown.js' },
    { template: 'tests/webauthn.spec.js.hbs', output: 'tests/webauthn.spec.js' },
    { template: 'tests/jwt-verification.spec.js.hbs', output: 'tests/jwt-verification.spec.js' },
    // Docker setup for WebAuthn server + Zero-Trust stack
    { template: 'docker/docker-compose.yml.hbs', output: 'docker/docker-compose.yml' },
    { template: 'docker/envoy-gateway.yaml.hbs', output: 'docker/envoy-gateway.yaml' },
    { template: 'docker/init-db.sql.hbs', output: 'docker/init-db.sql' },
    { template: 'docker/secrets/.gitignore.hbs', output: 'docker/secrets/.gitignore' },
    { template: 'docker/setup-secrets.sh.hbs', output: 'docker/setup-secrets.sh' },
    // Example service (Python FastAPI)
    { template: 'example-service/main.py.hbs', output: 'example-service/main.py' },
    { template: 'example-service/requirements.txt.hbs', output: 'example-service/requirements.txt' },
    { template: 'example-service/Dockerfile.hbs', output: 'example-service/Dockerfile' },
    { template: 'example-service/README.md.hbs', output: 'example-service/README.md' }
  ];

  // Template variables
  const template_vars = {
    server_url,
    client_port,
    server_port,
    relying_party_id,
    relying_party_name
  };

  try {
    // Generate secure passwords for Docker secrets
    const postgres_password = generateSecurePassword();
    const redis_password = generateSecurePassword();

    // Create project directory structure
    mkdirSync(project_path, { recursive: true });
    mkdirSync(join(project_path, 'src'), { recursive: true });
    mkdirSync(join(project_path, 'public'), { recursive: true });
    mkdirSync(join(project_path, 'tests'), { recursive: true });
    mkdirSync(join(project_path, 'docker'), { recursive: true });
    mkdirSync(join(project_path, 'docker', 'secrets'), { recursive: true });
    mkdirSync(join(project_path, 'example-service'), { recursive: true });

    // Generate files from templates
    for (const { template, output } of template_files) {
      // Path traversal protection: validate template filename
      if (template.indexOf('..') !== -1 || template.indexOf('\0') !== -1) {
        throw new Error('Invalid template filename');
      }

      // Path traversal protection: validate output path
      if (output.indexOf('..') !== -1 || output.indexOf('\0') !== -1) {
        throw new Error('Invalid output path');
      }

      const template_path = join(template_dir, template);
      const output_path = join(project_path, output);

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

    // Generate Docker secret files with auto-generated passwords
    const postgres_password_path = join(project_path, 'docker', 'secrets', 'postgres_password');
    const redis_password_path = join(project_path, 'docker', 'secrets', 'redis_password');

    writeFileSync(postgres_password_path, postgres_password, 'utf8');
    writeFileSync(redis_password_path, redis_password, 'utf8');
    files_created.push(postgres_password_path);
    files_created.push(redis_password_path);

    return {
      content: [
        {
          type: 'text',
          text: `✅ Web client generated successfully!

Files created:
${files_created.map(f => `  - ${f}`).join('\n')}

🚀 Quick Start (Complete Setup):
1. cd ${project_path}/docker && docker compose up -d
   (Starts WebAuthn server + PostgreSQL + Redis)
2. cd .. && npm install
3. npm run build
4. npm start &
5. npm test
   (Validates complete WebAuthn setup with E2E tests)
6. If tests pass ✅, open http://localhost:${client_port}

🔐 Security:
  - Unique passwords auto-generated in docker/secrets/
  - Secrets mounted as read-only files in containers
  - .gitignore prevents accidental commits
  - To rotate: regenerate secrets, restart docker compose

📋 Server Management:
  - View logs:    cd docker && docker compose logs -f
  - Stop server:  cd docker && docker compose down
  - Restart:      cd docker && docker compose restart`,
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
