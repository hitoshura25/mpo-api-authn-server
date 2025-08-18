# Gradle Task Development - Code Review Checklist

This checklist ensures all Gradle task development follows configuration cache best practices and prevents recurring compatibility issues.

## 🔍 Pre-Review: Automated Validation

**Before manual review, run these automated checks:**

```bash
# Test configuration cache compatibility
./gradlew [your-task-name] --configuration-cache --info

# Verify cache reuse (should be significantly faster)
./gradlew [your-task-name] --configuration-cache --info

# Check for configuration cache warnings
./gradlew build --configuration-cache --configuration-cache-problems=warn
```

## ✅ Configuration Cache Compatibility

### Critical Issues (Must Fix)
- [ ] **NO project API access in execution blocks** (`doLast`, `doFirst`)
  - ❌ `project.rootDir`, `project.buildDir`, `project.version`
  - ❌ `Task.project` accessor usage
  - ❌ `project.findProperty()` in execution phase
- [ ] **NO direct file() calls in execution blocks**
  - ❌ `file("${project.rootDir}/path")` in `doLast`
  - ❌ `file("${project.buildDir}/output")` in execution
- [ ] **All paths configured at configuration time**
  - ✅ Use `layout.projectDirectory.file("path")`
  - ✅ Use `layout.buildDirectory.dir("path")`
- [ ] **All project properties captured before execution**
  ```gradle
  // ✅ Configuration time
  def capturedVersion = project.version
  def customProp = project.findProperty('prop') ?: 'default'
  
  doLast {
    // ✅ Use captured values
    println "Version: ${capturedVersion}"
  }
  ```

### Best Practices
- [ ] **Provider API usage for dynamic paths**
  ```gradle
  def outputDir = layout.buildDirectory.dir("generated")
  doLast {
    def actualDir = outputDir.get().asFile  // ✅ Convert in execution
  }
  ```
- [ ] **Proper inputs/outputs declaration**
  ```gradle
  inputs.file(templateFile)   // For up-to-date checking
  outputs.dir(outputDir)      // For incremental builds
  ```
- [ ] **Task API vs Project API in execution**
  ```gradle
  doLast {
    copy {  // ✅ Task.copy method
      from 'src'
      into 'dest'  
    }
    // ❌ project.copy { } would break config cache
  }
  ```

## 🧪 Template Processing Tasks

**Special focus for client library generation tasks:**

- [ ] **Template file paths configured at configuration time**
  ```gradle
  def templateFile = layout.projectDirectory.file("templates/template.json")
  ```
- [ ] **All template variables captured before execution**
  ```gradle
  def packageName = project.findProperty('npmName') ?: 'default-name'
  def version = project.version
  ```
- [ ] **Template existence validation in execution phase**
  ```gradle
  doLast {
    def actualTemplateFile = templateFile.asFile
    if (actualTemplateFile.exists()) {
      // Process template with captured variables
    }
  }
  ```
- [ ] **Generated files created using captured paths**
  ```gradle
  new File(actualOutputDir, 'generated.json').text = processedContent
  ```

## 📝 File Operations

- [ ] **Copy operations use captured paths**
  ```gradle
  copy {
    from actualSourceDir    // ✅ Captured at configuration time
    into actualTargetDir    // ✅ Captured at configuration time
  }
  ```
- [ ] **File existence checks in execution phase only**
  ```gradle
  doLast {
    if (actualFile.exists()) {  // ✅ Check during execution
      // Process file
    }
  }
  ```
- [ ] **Text processing uses captured variables**
  ```gradle
  actualFile.text = template
    .replace('{{VERSION}}', capturedVersion)    // ✅ Use captured value
    .replace('{{NAME}}', capturedName)          // ✅ Use captured value
  ```

## 🔧 Task Configuration

- [ ] **Task dependencies declared properly**
  ```gradle
  dependsOn generateClient    // ✅ Static dependency
  ```
- [ ] **Task inputs/outputs comprehensive**
  ```gradle
  inputs.dir(sourceDir)       // All input directories
  inputs.file(templateFile)   // All input files  
  outputs.dir(targetDir)      // All output directories
  outputs.file(generatedFile) // All output files
  ```
- [ ] **Task description provided**
  ```gradle
  description = "Processes client library templates"
  group = "client generation"
  ```

## 🚨 Common Anti-Patterns to Reject

### Immediate Rejection Criteria
- [ ] **`project.rootDir` in `doLast` block** - Breaks configuration cache
- [ ] **`project.buildDir` in execution phase** - Use `layout.buildDirectory`
- [ ] **`Task.project` accessor usage** - Capture properties at configuration time
- [ ] **Dynamic property access in execution** - `project.findProperty()` in `doLast`
- [ ] **File path construction in execution** - Configure all paths beforehand

### Warning Signs (Needs Investigation)
- [ ] **Complex conditional logic in execution** - May hide configuration issues
- [ ] **String concatenation with project properties** - Could be accessing project API
- [ ] **Late-bound file operations** - Paths should be configured early
- [ ] **Missing inputs/outputs** - Breaks incremental build and caching

## 📋 Testing Requirements

### Mandatory Testing Steps
- [ ] **Clean build with configuration cache**
  ```bash
  ./gradlew clean [task-name] --configuration-cache
  ```
- [ ] **Verify cache reuse (second run should be fast)**
  ```bash
  ./gradlew [task-name] --configuration-cache --info | grep "FROM-CACHE\|UP-TO-DATE"
  ```
- [ ] **Check generated outputs exist and are correct**
  ```bash
  ls -la [expected-output-path]
  cat [generated-file] | jq '.' # Validate JSON structure
  ```
- [ ] **Template processing verification**
  ```bash
  # Verify template variables were replaced
  grep -v "{{.*}}" [generated-file] || echo "Unreplaced template variables found"
  ```

### Integration Testing
- [ ] **End-to-end workflow testing**
  - Client generation → Template processing → Publishing workflow
- [ ] **Cross-platform compatibility**
  - Test on both Android and TypeScript client generation
- [ ] **Publishing workflow compatibility**
  - Verify generated files work with publishing tasks

## 🎯 Specific Client Library Patterns

### Android Client Library Tasks
- [ ] **Android template processing follows patterns**
  ```gradle
  def androidTemplateFile = layout.projectDirectory.file("android-client-library/build.gradle.kts.template")
  def packageName = project.findProperty('androidPackageName') ?: 'default'
  ```
- [ ] **Generated Android files in correct locations**
  ```gradle
  def androidClientDir = layout.projectDirectory.dir("android-client-library")
  ```

### TypeScript Client Library Tasks
- [ ] **npm package.json template processing**
  ```gradle
  def packageJsonTemplate = layout.projectDirectory.file("typescript-client-library/package.json.template")
  def npmName = project.findProperty('npmName') ?: 'default-package'
  ```
- [ ] **TypeScript source file generation**
  ```gradle
  def typescriptSrcDir = layout.projectDirectory.dir("typescript-client-library/src")
  ```

## ⚡ Performance Considerations

- [ ] **Task marked as cacheable if appropriate**
  ```gradle
  @CacheableTask  // If task produces deterministic outputs
  ```
- [ ] **Incremental build support**
  ```gradle
  @InputDirectory
  @OutputDirectory
  ```
- [ ] **Avoid unnecessary work in execution phase**
  - Pre-compute values at configuration time
  - Use Provider API for lazy evaluation

## 📚 Documentation Requirements

- [ ] **Task purpose clearly documented**
- [ ] **Configuration cache compatibility verified**
- [ ] **Integration points with other tasks documented**
- [ ] **Troubleshooting notes for common issues**

## 🔄 Review Process Integration

### For Reviewers
1. **Run automated validation commands first**
2. **Check code against this checklist systematically**
3. **Reject immediately if any critical issues found**
4. **Test configuration cache compatibility locally**
5. **Verify template processing works end-to-end**

### For Developers
1. **Self-review using this checklist before submitting**
2. **Include test results in PR description**
3. **Document any deviations from standard patterns**
4. **Add debugging output for complex template processing**

## 🚨 Escalation Criteria

**Escalate to architecture review if:**
- Task requires project API access during execution
- Complex cross-task dependencies make configuration cache difficult
- Template processing has dynamic requirements that conflict with static configuration
- Performance requirements conflict with configuration cache compatibility

## ✅ Sign-off Checklist

**Before approving any Gradle task changes:**

- [ ] All automated tests pass with `--configuration-cache`
- [ ] No configuration cache warnings in build output
- [ ] Template processing verified to work correctly
- [ ] Generated files appear in expected locations with correct content
- [ ] Integration with publishing workflows tested
- [ ] Documentation updated to reflect any new patterns

---

**Remember**: Configuration cache compatibility is not optional. Any task that breaks configuration cache must be fixed before merge, as it will impact build performance and reliability for all developers.