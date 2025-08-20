# Gradle Configuration Cache Compatibility

This document outlines critical patterns for writing Gradle tasks compatible with Gradle's configuration cache feature. These patterns are essential for client library generation, publishing workflows, and any custom Gradle task development.

## Overview

Gradle's configuration cache improves build performance by caching the configuration phase results. However, it requires strict separation between configuration-time and execution-time code, leading to subtle but critical compatibility issues.

## Critical Configuration Cache Rules

### ❌ NEVER: Access Project Properties in Execution Phase

**Problem**: Using `project.rootDir`, `Task.project`, or other project accessors inside `doLast` blocks breaks configuration cache.

**Warning Signs**:
- "invocation of 'Task.project' at execution time is unsupported"
- Template processing fails silently
- Generated files don't appear in expected locations
- Tasks report "task not found" errors despite being defined

**Example of BROKEN code**:
```gradle
// ❌ BROKEN: Accessing project in doLast
task processTemplate {
    doLast {
        def templateFile = file("${project.rootDir}/templates/client.template")  // ❌ BAD
        def outputDir = file("${project.buildDir}/generated")                    // ❌ BAD
        
        // This breaks configuration cache!
        templateFile.text = processTemplate(templateFile.text, project.version) // ❌ BAD
    }
}
```

### ✅ CORRECT: Use Provider API and Configure Paths at Configuration Time

**Solution**: Configure all paths and properties during configuration phase, then access them safely during execution.

**Example of CORRECT code**:
```gradle
// ✅ CORRECT: Configuration cache compatible
task processTemplate {
    // Configure paths at configuration time
    def templateFile = layout.projectDirectory.file("templates/client.template")
    def outputDir = layout.buildDirectory.dir("generated") 
    def projectVersion = project.version  // Capture at configuration time
    
    inputs.file(templateFile)
    outputs.dir(outputDir)
    
    doLast {
        // Safe to access configured values in execution phase  
        def actualTemplateFile = templateFile.asFile         // ✅ GOOD
        def actualOutputDir = outputDir.get().asFile         // ✅ GOOD
        
        actualTemplateFile.text = processTemplate(
            actualTemplateFile.text, 
            projectVersion  // Use captured value, not project.version
        )
    }
}
```

## Real-World Example: Client Library Template Processing

### Problem Case (Before Fix)
```gradle
task copyTsClientToSubmodule {
    dependsOn generateTsClient
    
    doLast {
        // ❌ This broke configuration cache
        def sourceDir = file("${project.rootDir}/build/generated-clients/typescript")
        def targetDir = file("${project.rootDir}/typescript-client-library")
        def templateFile = file("${targetDir}/package.json.template")
        
        // Template processing failed silently due to configuration cache
        if (templateFile.exists()) {
            def packageJson = templateFile.text
                .replace('{{NPM_PACKAGE_NAME}}', project.findProperty('npmName') ?: 'mpo-webauthn-client')
                .replace('{{CLIENT_VERSION}}', project.version)
            
            file("${targetDir}/package.json").text = packageJson
        }
    }
}
```

**Symptoms**: 
- Template file never processed
- `package.json` remained unchanged
- Client publishing failed with "task not found" errors
- No obvious error messages

### Solution (After Fix)
```gradle
task copyTsClientToSubmodule {
    dependsOn generateTsClient
    
    // ✅ Configure all paths and properties at configuration time
    def sourceDir = layout.projectDirectory.dir("build/generated-clients/typescript")
    def targetDir = layout.projectDirectory.dir("typescript-client-library")  
    def templateFile = layout.projectDirectory.file("typescript-client-library/package.json.template")
    
    // Capture project properties at configuration time
    def npmPackageName = project.findProperty('npmName') ?: 'mpo-webauthn-client'
    def clientVersion = project.version
    
    inputs.dir(sourceDir)
    inputs.file(templateFile)
    outputs.dir(targetDir)
    
    doLast {
        // ✅ Safe to use configured values in execution phase
        def actualSourceDir = sourceDir.get().asFile
        def actualTargetDir = targetDir.get().asFile  
        def actualTemplateFile = templateFile.asFile
        
        // Copy generated client files
        copy {
            from actualSourceDir
            into actualTargetDir
            exclude 'package.json.template'
        }
        
        // Process template with captured values
        if (actualTemplateFile.exists()) {
            def packageJson = actualTemplateFile.text
                .replace('{{NPM_PACKAGE_NAME}}', npmPackageName)    // ✅ Use captured value
                .replace('{{CLIENT_VERSION}}', clientVersion)       // ✅ Use captured value
            
            new File(actualTargetDir, 'package.json').text = packageJson
        }
    }
}
```

## Key Patterns for Configuration Cache Compatibility

### 1. Path Configuration Pattern
```gradle
// ✅ Use layout API for all paths
def sourceFile = layout.projectDirectory.file("src/template.txt")
def outputDir = layout.buildDirectory.dir("generated")

doLast {
    def actualFile = sourceFile.asFile      // Convert to File in execution phase
    def actualDir = outputDir.get().asFile  // Use .get().asFile for Provider<Directory>
}
```

### 2. Property Capture Pattern  
```gradle
// ✅ Capture project properties at configuration time
def version = project.version
def customProperty = project.findProperty('customProp') ?: 'default'

doLast {
    // Use captured values, not project.* directly
    println "Version: ${version}"           // ✅ GOOD
    println "Custom: ${customProperty}"     // ✅ GOOD
    // println "Bad: ${project.version}"    // ❌ BAD - would break config cache
}
```

### 3. File Operations Pattern
```gradle
// ✅ Configure file references at configuration time
def inputFile = layout.projectDirectory.file("input.txt")
def outputFile = layout.buildDirectory.file("output.txt")

inputs.file(inputFile)   // Declare inputs for up-to-date checking
outputs.file(outputFile) // Declare outputs for up-to-date checking

doLast {
    def actualInputFile = inputFile.asFile
    def actualOutputFile = outputFile.get().asFile
    
    actualOutputFile.text = actualInputFile.text.toUpperCase()
}
```

### 4. Conditional Logic Pattern
```gradle
// ✅ Evaluate conditions at configuration time when possible
def shouldProcess = project.hasProperty('processTemplates')

doLast {
    if (shouldProcess) {    // Use captured boolean
        // Process templates
    }
}

// For dynamic conditions, capture the evaluation logic
def templateExists = layout.projectDirectory.file("template.txt").asFile.exists()

doLast {
    if (templateExists) {   // Use pre-evaluated condition
        // Process template
    }
}
```

## Common Pitfalls and Solutions

### Pitfall 1: Late Property Access
```gradle
// ❌ WRONG: Accessing project properties in doLast
doLast {
    def version = project.version  // Breaks configuration cache
}

// ✅ RIGHT: Capture properties at configuration time
def version = project.version
doLast {
    println "Version: ${version}"  // Use captured value
}
```

### Pitfall 2: File Path Construction in Execution
```gradle
// ❌ WRONG: Constructing paths in doLast
doLast {
    def file = file("${project.rootDir}/build/output.txt")  // Breaks configuration cache
}

// ✅ RIGHT: Configure paths at configuration time
def outputFile = layout.projectDirectory.file("build/output.txt")
doLast {
    def actualFile = outputFile.asFile  // Convert in execution phase
}
```

### Pitfall 3: Project API Usage in Execution
```gradle
// ❌ WRONG: Using project API in doLast
doLast {
    project.copy {  // Breaks configuration cache
        from 'src'
        into 'dest'
    }
}

// ✅ RIGHT: Use task API in execution phase
doLast {
    copy {  // Uses task copy method, not project.copy
        from 'src'  
        into 'dest'
    }
}
```

## Debugging Configuration Cache Issues

### 1. Enable Configuration Cache Warnings
```bash
# Run with configuration cache warnings enabled
./gradlew build --configuration-cache --configuration-cache-problems=warn
```

### 2. Identify Problematic Tasks
Look for warnings like:
- "invocation of 'Task.project' at execution time is unsupported"
- "reading a property of 'Task.project' at execution time is unsupported"
- Configuration cache entry stored with X problem(s)

### 3. Validate Template Processing
```gradle
// Add debugging to verify template processing
doLast {
    println "Processing template at: ${actualTemplateFile.absolutePath}"
    println "Template exists: ${actualTemplateFile.exists()}"
    println "Template content length: ${actualTemplateFile.length()}"
}
```

### 4. Test Configuration Cache Compatibility
```bash
# Test that tasks work with configuration cache enabled
./gradlew clean build --configuration-cache

# Run twice to verify cache loading works
./gradlew build --configuration-cache
```

## Integration with Client Library Workflows

### Template Processing Tasks
All client library template processing tasks (Android and TypeScript) must follow these patterns:

1. **Configure template paths at configuration time**
2. **Capture all project properties before execution phase** 
3. **Use layout API for all file operations**
4. **Validate template existence and processing in execution phase**

### Publishing Tasks
Publishing tasks that generate configuration files must:

1. **Pre-configure all output directories**
2. **Capture version and package naming properties**
3. **Use Provider API for dynamic file locations**
4. **Avoid project API access during execution**

## Testing Configuration Cache Compatibility

### Validation Checklist
- [ ] Task runs successfully with `--configuration-cache` flag
- [ ] Task produces identical output on second run (cache hit)  
- [ ] No warnings about execution-time project access
- [ ] Template files are processed correctly
- [ ] Generated files appear in expected locations
- [ ] Publishing workflows complete successfully

### Test Commands
```bash
# Test configuration cache compatibility
./gradlew copyTsClientToSubmodule --configuration-cache --info

# Verify cache reuse
./gradlew copyTsClientToSubmodule --configuration-cache --info

# Test with clean build
./gradlew clean copyTsClientToSubmodule --configuration-cache

# Validate generated outputs
ls -la typescript-client-library/package.json
cat typescript-client-library/package.json | jq '.name, .version'
```

## Conclusion

Configuration cache compatibility requires disciplined separation of configuration and execution phases. By following these patterns, we ensure that:

1. **Client library generation works reliably** with configuration cache enabled
2. **Template processing completes successfully** without silent failures  
3. **Publishing workflows remain fast** while maintaining correctness
4. **Future Gradle task development** follows established best practices

Always test custom Gradle tasks with `--configuration-cache` enabled to catch compatibility issues early in development.