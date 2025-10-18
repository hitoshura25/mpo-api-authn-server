import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import Handlebars from 'handlebars';
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
export async function generateWebClient(args) {
    const { project_path, framework = 'vanilla', server_url = 'http://localhost:8080', client_port = 8082 } = args;
    // Validate framework
    if (!['vanilla', 'react', 'vue'].includes(framework)) {
        throw new Error(`Unsupported framework: ${framework}. Use 'vanilla', 'react', or 'vue'.`);
    }
    // Check if directory exists
    if (existsSync(project_path)) {
        throw new Error(`Directory already exists: ${project_path}. Please choose a different path or remove the existing directory.`);
    }
    const files_created = [];
    const template_dir = join(__dirname, '..', 'templates', framework);
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
        // Create project directory structure
        mkdirSync(project_path, { recursive: true });
        mkdirSync(join(project_path, 'src'), { recursive: true });
        mkdirSync(join(project_path, 'public'), { recursive: true });
        // Generate files from templates
        for (const { template, output } of template_files) {
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
        return {
            content: [
                {
                    type: 'text',
                    text: `✅ Web client generated successfully!\n\nFiles created:\n${files_created.map(f => `  - ${f}`).join('\n')}\n\nNext steps:\n1. cd ${project_path}\n2. npm install\n3. npm run build\n4. npm start\n5. Open http://localhost:${client_port}`,
                },
            ],
        };
    }
    catch (error) {
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
