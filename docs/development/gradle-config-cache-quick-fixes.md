# Gradle Configuration Cache - Quick Fix Reference

Quick reference for fixing common Gradle configuration cache compatibility issues. Use this as a first-aid guide during development.

## 🚨 Emergency Patterns: Fix These Immediately

### ❌ Project API Access in Execution
```gradle
// ❌ BROKEN - Will break configuration cache
doLast {
    def file = file("${project.rootDir}/template.txt")
    def output = file("${project.buildDir}/output")
    def version = project.version
}
```

```gradle
// ✅ FIXED - Configuration cache compatible  
def templateFile = layout.projectDirectory.file("template.txt")
def outputDir = layout.buildDirectory.dir("output")
def capturedVersion = project.version

doLast {
    def actualFile = templateFile.asFile
    def actualDir = outputDir.get().asFile
    // Use capturedVersion, not project.version
}
```

### ❌ Template Processing Failures
```gradle
// ❌ BROKEN - Template never processed
doLast {
    def template = file("${project.rootDir}/templates/package.json.template")
    template.text = template.text.replace('{{VERSION}}', project.version)
}
```

```gradle  
// ✅ FIXED - Template processing works
def templateFile = layout.projectDirectory.file("templates/package.json.template")
def packageVersion = project.version

inputs.file(templateFile)
outputs.file(layout.projectDirectory.file("package.json"))

doLast {
    def actualTemplate = templateFile.asFile
    if (actualTemplate.exists()) {
        def content = actualTemplate.text.replace('{{VERSION}}', packageVersion)
        new File(actualTemplate.parentFile, "package.json").text = content
    }
}
```

### ❌ Copy Task Failures
```gradle
// ❌ BROKEN - Paths resolved at execution time
doLast {
    copy {
        from "${project.rootDir}/src"
        into "${project.buildDir}/dest"
    }
}
```

```gradle
// ✅ FIXED - Paths configured beforehand
def sourceDir = layout.projectDirectory.dir("src")  
def destDir = layout.buildDirectory.dir("dest")

inputs.dir(sourceDir)
outputs.dir(destDir)

doLast {
    copy {
        from sourceDir.get().asFile
        into destDir.get().asFile
    }
}
```

## 🔧 Quick Diagnostic Commands

```bash
# Test if task works with configuration cache
./gradlew [taskName] --configuration-cache --info

# Check for configuration cache problems
./gradlew build --configuration-cache --configuration-cache-problems=warn

# Verify cache reuse (should be much faster)  
./gradlew [taskName] --configuration-cache --info
```

## 📋 Common Error Messages → Fixes

### "invocation of 'Task.project' at execution time is unsupported"
**Fix**: Capture project properties at configuration time
```gradle
// Before doLast block
def capturedProperty = project.findProperty('prop') ?: 'default'
```

### Template files not being processed / Generated files missing
**Fix**: Configure file paths using `layout` API
```gradle
def templateFile = layout.projectDirectory.file("path/to/template")
def outputFile = layout.buildDirectory.file("path/to/output")
```

### "Configuration cache entry stored with problems" 
**Fix**: Remove ALL `project.*` access from execution blocks
```gradle
// Move to configuration time
def version = project.version
def rootDir = layout.projectDirectory
```

## 🎯 Client Library Template Processing Pattern

Use this exact pattern for all client library template processing:

```gradle
task processClientTemplate {
    // Configuration time setup
    def templateFile = layout.projectDirectory.file("client-library/template.json")
    def outputFile = layout.projectDirectory.file("client-library/generated.json") 
    def packageName = project.findProperty('packageName') ?: 'default-name'
    def clientVersion = project.version
    def customProp = project.findProperty('customProp') ?: 'default-value'
    
    inputs.file(templateFile)
    outputs.file(outputFile)
    
    doLast {
        def actualTemplate = templateFile.asFile
        def actualOutput = outputFile.asFile
        
        if (actualTemplate.exists()) {
            def content = actualTemplate.text
                .replace('{{PACKAGE_NAME}}', packageName)
                .replace('{{VERSION}}', clientVersion)  
                .replace('{{CUSTOM_PROP}}', customProp)
                
            actualOutput.text = content
            println "Generated: ${actualOutput.absolutePath}"
        } else {
            throw new GradleException("Template not found: ${actualTemplate.absolutePath}")
        }
    }
}
```

## ⚡ Performance Testing Pattern

Always test with these commands after making changes:

```bash
# Clean build with configuration cache
./gradlew clean processClientTemplate --configuration-cache

# Verify cache hit (should be much faster)
./gradlew processClientTemplate --configuration-cache --info

# Look for "FROM-CACHE" or "UP-TO-DATE" in output
```

## 🚨 Integration Gotchas

### Android Client Library Tasks
```gradle
// ✅ Correct Android template processing
def androidTemplate = layout.projectDirectory.file("android-client-library/build.gradle.kts.template")
def androidPackage = project.findProperty('androidPackageName') ?: 'com.example.client'
```

### TypeScript Client Library Tasks  
```gradle
// ✅ Correct TypeScript template processing
def tsTemplate = layout.projectDirectory.file("typescript-client-library/package.json.template")
def npmName = project.findProperty('npmPackageName') ?: '@example/client'
```

### Publishing Integration
```gradle
// ✅ Generated files must be available for publishing tasks
outputs.dir(layout.projectDirectory.dir("client-library"))  // Declare all outputs
```

## 🔄 Before Submitting PR

**Mandatory checklist:**
- [ ] `./gradlew [taskName] --configuration-cache` passes
- [ ] Second run shows cache hit or is much faster  
- [ ] Template processing verified (check generated files)
- [ ] No "Task.project" warnings in output
- [ ] Integration with publishing workflows tested

## 📞 When to Escalate

**Escalate to architecture review if:**
- Task genuinely requires dynamic project access during execution
- Configuration cache compatibility conflicts with functional requirements  
- Complex template processing doesn't fit standard patterns
- Performance requirements conflict with configuration cache best practices

---

**Remember**: Configuration cache is not negotiable. Any violation must be fixed before merge.