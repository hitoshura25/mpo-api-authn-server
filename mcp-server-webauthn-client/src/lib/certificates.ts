/**
 * Certificate Generation for mTLS (Phase 2: Istio Service Mesh)
 *
 * Generates self-signed certificates for zero-trust mTLS communication:
 * - CA certificate (Certificate Authority for the mesh)
 * - Envoy Gateway certificate (signed by CA)
 * - Example Service certificate (signed by CA)
 *
 * All certificates valid for 365 days.
 */

import { execSync } from 'child_process';
import { mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';

export interface CertificateGenerationResult {
  certsDir: string;
  filesCreated: string[];
}

/**
 * Generate all mTLS certificates for the zero-trust stack
 */
export function generateMTLSCertificates(projectPath: string): CertificateGenerationResult {
  const certsDir = join(projectPath, 'docker', 'certs');
  mkdirSync(certsDir, { recursive: true });

  const filesCreated: string[] = [];

  console.log('🔐 Generating mTLS certificates...');

  // 1. Generate CA (Certificate Authority)
  console.log('   Generating CA certificate...');
  execSync(
    `openssl req -x509 -newkey rsa:2048 -nodes \\
      -keyout "${join(certsDir, 'ca-key.pem')}" \\
      -out "${join(certsDir, 'ca-cert.pem')}" \\
      -days 365 \\
      -subj "/CN=WebAuthn-Mesh-CA/O=WebAuthn/OU=Zero-Trust"`,
    { stdio: 'inherit' }
  );
  filesCreated.push(join(certsDir, 'ca-key.pem'));
  filesCreated.push(join(certsDir, 'ca-cert.pem'));

  // 2. Generate Envoy Gateway certificate
  console.log('   Generating Envoy Gateway certificate...');

  // Generate key and CSR
  execSync(
    `openssl req -newkey rsa:2048 -nodes \\
      -keyout "${join(certsDir, 'gateway-key.pem')}" \\
      -out "${join(certsDir, 'gateway-csr.pem')}" \\
      -subj "/CN=envoy-gateway/O=WebAuthn/OU=Gateway"`,
    { stdio: 'inherit' }
  );

  // Sign with CA
  execSync(
    `openssl x509 -req \\
      -in "${join(certsDir, 'gateway-csr.pem')}" \\
      -CA "${join(certsDir, 'ca-cert.pem')}" \\
      -CAkey "${join(certsDir, 'ca-key.pem')}" \\
      -CAcreateserial \\
      -out "${join(certsDir, 'gateway-cert.pem')}" \\
      -days 365`,
    { stdio: 'inherit' }
  );

  filesCreated.push(join(certsDir, 'gateway-key.pem'));
  filesCreated.push(join(certsDir, 'gateway-cert.pem'));

  // 3. Generate Example Service certificate
  console.log('   Generating Example Service certificate...');

  // Generate key and CSR
  execSync(
    `openssl req -newkey rsa:2048 -nodes \\
      -keyout "${join(certsDir, 'service-key.pem')}" \\
      -out "${join(certsDir, 'service-csr.pem')}" \\
      -subj "/CN=example-service/O=WebAuthn/OU=Services"`,
    { stdio: 'inherit' }
  );

  // Sign with CA
  execSync(
    `openssl x509 -req \\
      -in "${join(certsDir, 'service-csr.pem')}" \\
      -CA "${join(certsDir, 'ca-cert.pem')}" \\
      -CAkey "${join(certsDir, 'ca-key.pem')}" \\
      -CAcreateserial \\
      -out "${join(certsDir, 'service-cert.pem')}" \\
      -days 365`,
    { stdio: 'inherit' }
  );

  filesCreated.push(join(certsDir, 'service-key.pem'));
  filesCreated.push(join(certsDir, 'service-cert.pem'));

  // 4. Create .gitignore to prevent committing private keys
  const gitignoreContent = `# mTLS Certificates - Auto-generated
# DO NOT commit private keys to version control!
*.pem
*.csr
*.srl
`;

  writeFileSync(join(certsDir, '.gitignore'), gitignoreContent);
  filesCreated.push(join(certsDir, '.gitignore'));

  // 5. Create README explaining the certificates
  const readmeContent = `# mTLS Certificates

Auto-generated certificates for zero-trust mTLS communication.

## Certificate Authority (CA)
- \`ca-cert.pem\` - CA certificate (public, trusted by all services)
- \`ca-key.pem\` - CA private key (used to sign service certificates)

## Envoy Gateway
- \`gateway-cert.pem\` - Gateway certificate (signed by CA)
- \`gateway-key.pem\` - Gateway private key

## Example Service
- \`service-cert.pem\` - Service certificate (signed by CA)
- \`service-key.pem\` - Service private key

## Validity
All certificates are valid for 365 days from generation.

## Rotation
To rotate certificates, delete this directory and regenerate the client.

## Security Notes
- ⚠️ DO NOT commit \`.pem\` files to version control
- ⚠️ Private keys (\`*-key.pem\`) must be kept secure
- ✅ Certificates are automatically ignored by git
- ✅ Each generation creates unique certificates
`;

  writeFileSync(join(certsDir, 'README.md'), readmeContent);
  filesCreated.push(join(certsDir, 'README.md'));

  console.log('✅ mTLS certificates generated successfully');

  return {
    certsDir,
    filesCreated
  };
}
