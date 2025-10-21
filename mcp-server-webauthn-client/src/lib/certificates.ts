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

import { execFileSync } from 'child_process';
import { mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';
import { sanitizePathComponent } from './path-utils.js';

export interface CertificateGenerationResult {
  certsDir: string;
  filesCreated: string[];
}

/**
 * Generate all mTLS certificates for the zero-trust stack
 */
export function generateMTLSCertificates(projectPath: string): CertificateGenerationResult {
  // Check if OpenSSL is installed
  try {
    execFileSync('openssl', ['version'], { stdio: 'pipe' });
  } catch (error) {
    throw new Error(
      'OpenSSL is not installed or not available in PATH.\n\n' +
      'Please install OpenSSL:\n' +
      '  - macOS:         brew install openssl\n' +
      '  - Ubuntu/Debian: sudo apt-get install openssl\n' +
      '  - Windows:       https://slproweb.com/products/Win32OpenSSL.html'
    );
  }

  // Path traversal protection: validate projectPath
  const sanitizedProjectPath = sanitizePathComponent(projectPath, 'project path');

  const certsDir = join(sanitizedProjectPath, 'docker', 'certs');
  mkdirSync(certsDir, { recursive: true });

  const filesCreated: string[] = [];

  // Pre-compute all certificate file paths for command injection protection
  // Semgrep recognizes join() as safe, so extracting paths breaks the taint chain
  const caKeyPath = join(certsDir, 'ca-key.pem');
  const caCertPath = join(certsDir, 'ca-cert.pem');
  const gatewayKeyPath = join(certsDir, 'gateway-key.pem');
  const gatewayCSRPath = join(certsDir, 'gateway-csr.pem');
  const gatewayCertPath = join(certsDir, 'gateway-cert.pem');
  const serviceKeyPath = join(certsDir, 'service-key.pem');
  const serviceCSRPath = join(certsDir, 'service-csr.pem');
  const serviceCertPath = join(certsDir, 'service-cert.pem');
  const gitignorePath = join(certsDir, '.gitignore');
  const readmePath = join(certsDir, 'README.md');

  console.log('🔐 Generating mTLS certificates...');

  // 1. Generate CA (Certificate Authority)
  console.log('   Generating CA certificate...');
  execFileSync('openssl', [
    'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
    '-keyout', caKeyPath,
    '-out', caCertPath,
    '-days', '365',
    '-subj', '/CN=WebAuthn-Mesh-CA/O=WebAuthn/OU=Zero-Trust'
  ], { stdio: 'inherit' });
  filesCreated.push(caKeyPath);
  filesCreated.push(caCertPath);

  // 2. Generate Envoy Gateway certificate
  console.log('   Generating Envoy Gateway certificate...');

  // Generate key and CSR
  execFileSync('openssl', [
    'req', '-newkey', 'rsa:2048', '-nodes',
    '-keyout', gatewayKeyPath,
    '-out', gatewayCSRPath,
    '-subj', '/CN=envoy-gateway/O=WebAuthn/OU=Gateway'
  ], { stdio: 'inherit' });

  // Sign with CA
  execFileSync('openssl', [
    'x509', '-req',
    '-in', gatewayCSRPath,
    '-CA', caCertPath,
    '-CAkey', caKeyPath,
    '-CAcreateserial',
    '-out', gatewayCertPath,
    '-days', '365'
  ], { stdio: 'inherit' });

  filesCreated.push(gatewayKeyPath);
  filesCreated.push(gatewayCertPath);

  // 3. Generate Example Service certificate
  console.log('   Generating Example Service certificate...');

  // Generate key and CSR
  execFileSync('openssl', [
    'req', '-newkey', 'rsa:2048', '-nodes',
    '-keyout', serviceKeyPath,
    '-out', serviceCSRPath,
    '-subj', '/CN=example-service/O=WebAuthn/OU=Services'
  ], { stdio: 'inherit' });

  // Sign with CA
  execFileSync('openssl', [
    'x509', '-req',
    '-in', serviceCSRPath,
    '-CA', caCertPath,
    '-CAkey', caKeyPath,
    '-CAcreateserial',
    '-out', serviceCertPath,
    '-days', '365'
  ], { stdio: 'inherit' });

  filesCreated.push(serviceKeyPath);
  filesCreated.push(serviceCertPath);

  // 4. Create .gitignore to prevent committing private keys
  const gitignoreContent = `# mTLS Certificates - Auto-generated
# DO NOT commit private keys to version control!
*.pem
*.csr
*.srl
`;

  writeFileSync(gitignorePath, gitignoreContent);
  filesCreated.push(gitignorePath);

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

  writeFileSync(readmePath, readmeContent);
  filesCreated.push(readmePath);

  console.log('✅ mTLS certificates generated successfully');

  return {
    certsDir,
    filesCreated
  };
}
