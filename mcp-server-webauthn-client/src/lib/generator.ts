import { readFileSync, writeFileSync, mkdirSync, existsSync, chmodSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { randomBytes } from 'crypto';
import Handlebars from 'handlebars';
import { generateMTLSCertificates } from './certificates.js';
import { sanitizePathComponent } from './path-utils.js';

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
  forward_port?: number;
  relying_party_id?: string;
  relying_party_name?: string;
  // Infrastructure port customization
  postgres_host_port?: number;
  redis_host_port?: number;
  gateway_host_port?: number;
  gateway_admin_port?: number;
  // Jaeger tracing ports
  jaeger_ui_port?: number;
  jaeger_collector_http_port?: number;
  jaeger_collector_grpc_port?: number;
  jaeger_otlp_grpc_port?: number;
  jaeger_otlp_http_port?: number;
  jaeger_agent_compact_port?: number;
  jaeger_agent_binary_port?: number;
  jaeger_agent_config_port?: number;
}

export async function generateWebClient(args: GenerateWebClientArgs) {
  const {
    project_path,
    framework = 'vanilla',
    server_url = 'http://localhost:8000',  // Envoy Gateway (zero-trust entry point)
    forward_port = 8082,
    relying_party_id = 'localhost',
    relying_party_name = 'WebAuthn Demo',
    // Infrastructure ports
    postgres_host_port = 5432,
    redis_host_port = 6379,
    gateway_host_port = 8000,
    gateway_admin_port = 9901,
    // Jaeger ports
    jaeger_ui_port = 16686,
    jaeger_collector_http_port = 14268,
    jaeger_collector_grpc_port = 14250,
    jaeger_otlp_grpc_port = 4317,
    jaeger_otlp_http_port = 4318,
    jaeger_agent_compact_port = 6831,
    jaeger_agent_binary_port = 6832,
    jaeger_agent_config_port = 5778
  } = args;

  // Validate framework
  if (!['vanilla', 'react', 'vue'].includes(framework)) {
    throw new Error(`Unsupported framework: ${framework}. Use 'vanilla', 'react', or 'vue'.`);
  }

  // Path traversal protection: validate parameters
  sanitizePathComponent(framework, 'framework');
  const sanitizedProjectPath = sanitizePathComponent(project_path, 'project path');

  // Check if directory exists
  if (existsSync(sanitizedProjectPath)) {
    throw new Error(`Directory already exists: ${sanitizedProjectPath}. Please choose a different path or remove the existing directory.`);
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
    // Istio service mesh (Phase 2: mTLS sidecars)
    { template: 'docker/istio/example-service-envoy.yaml.hbs', output: 'docker/istio/example-service-envoy.yaml' },
    // Example service (Python FastAPI)
    { template: 'example-service/main.py.hbs', output: 'example-service/main.py' },
    { template: 'example-service/requirements.txt.hbs', output: 'example-service/requirements.txt' },
    { template: 'example-service/Dockerfile.hbs', output: 'example-service/Dockerfile' },
    { template: 'example-service/docker-entrypoint.sh.hbs', output: 'example-service/docker-entrypoint.sh' },
    { template: 'example-service/README.md.hbs', output: 'example-service/README.md' },
    // Phase 6-7: Documentation and helper scripts
    { template: 'docs/INTEGRATION.md.hbs', output: 'docs/INTEGRATION.md' },
    { template: 'scripts/add-service.sh.hbs', output: 'scripts/add-service.sh' }
  ];

  // Template variables
  const template_vars = {
    server_url,
    client_port: forward_port,  // Keep template variable as client_port for backward compatibility
    server_port,
    relying_party_id,
    relying_party_name,
    // Infrastructure ports
    postgres_host_port,
    redis_host_port,
    gateway_host_port,
    gateway_admin_port,
    // Jaeger ports
    jaeger_ui_port,
    jaeger_collector_http_port,
    jaeger_collector_grpc_port,
    jaeger_otlp_grpc_port,
    jaeger_otlp_http_port,
    jaeger_agent_compact_port,
    jaeger_agent_binary_port,
    jaeger_agent_config_port
  };

  try {
    // Generate secure passwords for Docker secrets
    const postgres_password = generateSecurePassword();
    const redis_password = generateSecurePassword();

    // Create project directory structure
    mkdirSync(sanitizedProjectPath, { recursive: true });
    mkdirSync(join(sanitizedProjectPath, 'src'), { recursive: true });
    mkdirSync(join(sanitizedProjectPath, 'public'), { recursive: true });
    mkdirSync(join(sanitizedProjectPath, 'tests'), { recursive: true });
    mkdirSync(join(sanitizedProjectPath, 'docker'), { recursive: true });
    mkdirSync(join(sanitizedProjectPath, 'docker', 'secrets'), { recursive: true });
    mkdirSync(join(sanitizedProjectPath, 'docker', 'istio'), { recursive: true });  // Phase 2: Istio sidecar configs
    mkdirSync(join(sanitizedProjectPath, 'example-service'), { recursive: true });
    mkdirSync(join(sanitizedProjectPath, 'docs'), { recursive: true });  // Phase 6-7: Documentation
    mkdirSync(join(sanitizedProjectPath, 'scripts'), { recursive: true });  // Phase 6-7: Helper scripts

    // Generate files from templates
    for (const { template, output } of template_files) {
      // Path traversal protection: validate template filename and output path
      sanitizePathComponent(template, 'template filename');
      sanitizePathComponent(output, 'output path');

      const template_path = join(template_dir, template);
      const output_path = join(sanitizedProjectPath, output);

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
    const postgres_password_path = join(sanitizedProjectPath, 'docker', 'secrets', 'postgres_password');
    const redis_password_path = join(sanitizedProjectPath, 'docker', 'secrets', 'redis_password');

    writeFileSync(postgres_password_path, postgres_password, 'utf8');
    writeFileSync(redis_password_path, redis_password, 'utf8');
    files_created.push(postgres_password_path);
    files_created.push(redis_password_path);

    // Phase 2: Generate mTLS certificates for zero-trust service mesh
    const cert_result = generateMTLSCertificates(sanitizedProjectPath);
    files_created.push(...cert_result.filesCreated);

    // Phase 6-7: Make add-service.sh executable
    const add_service_script = join(sanitizedProjectPath, 'scripts', 'add-service.sh');
    chmodSync(add_service_script, 0o755);  // rwxr-xr-x

    return {
      content: [
        {
          type: 'text',
          text: `✅ Web client generated successfully!

Files created:
${files_created.map(f => `  - ${f}`).join('\n')}

🚀 Quick Start (Complete Setup):
1. cd ${sanitizedProjectPath}/docker && docker compose up -d
   (Starts WebAuthn server + PostgreSQL + Redis)
2. cd .. && npm install
3. npm run build
4. npm start &
5. npm test
   (Validates complete WebAuthn setup with E2E tests)
6. If tests pass ✅, open http://localhost:${forward_port}

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
