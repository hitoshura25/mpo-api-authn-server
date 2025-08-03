#!/bin/bash
set -e

# Markdown Validation Script
# Validates markdown files for common syntax errors

echo "🔍 Validating Markdown Files..."

# Find all markdown files
MARKDOWN_FILES=$(find . -name "*.md" -not -path "./node_modules/*" -not -path "./.git/*" -not -path "./build/*" -not -path "./test-client/node_modules/*" -not -path "./*/node_modules/*")

TOTAL_FILES=0
ERROR_COUNT=0

for file in $MARKDOWN_FILES; do
    echo ""
    echo "📄 Checking: $file"
    TOTAL_FILES=$((TOTAL_FILES + 1))
    
    # Check 1: Balanced code blocks
    CODE_BLOCK_COUNT=$(grep -c '```' "$file" || true)
    if [ $((CODE_BLOCK_COUNT % 2)) -ne 0 ]; then
        echo "❌ ERROR: Unmatched code blocks (found $CODE_BLOCK_COUNT triple backticks)"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        echo "✅ Code blocks balanced ($((CODE_BLOCK_COUNT / 2)) pairs)"
    fi
    
    # Check 2: Unicode characters in code blocks
    UNICODE_IN_CODE=$(awk '
        /```/ { in_code = !in_code; next }
        in_code && /[^\x00-\x7F]/ { 
            print NR ": " $0 
            found = 1
        }
        END { exit found ? 1 : 0 }
    ' "$file" || true)
    
    if [ $? -eq 1 ]; then
        echo "❌ ERROR: Unicode characters found in code blocks:"
        echo "$UNICODE_IN_CODE"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        echo "✅ No unicode in code blocks"
    fi
    
    # Check 3: Mixed language tags in code blocks
    MIXED_SYNTAX=$(awk '
        /^```[a-z]+/ { 
            block_lang = substr($0, 4)
            in_code = 1
            line_start = NR
            next 
        }
        /^```$/ { 
            if (in_code) {
                in_code = 0
                block_lang = ""
            }
            next 
        }
        in_code {
            # Check for YAML in non-yaml blocks
            if (block_lang != "yaml" && /^[a-zA-Z_][a-zA-Z0-9_]*:(\s|$)/) {
                print "Line " NR ": YAML syntax in " block_lang " block: " $0
                found = 1
            }
            # Check for JSON in non-json blocks  
            if (block_lang != "json" && /^\s*["{[]/) {
                if (block_lang == "kotlin" || block_lang == "java") {
                    # Skip - these can have JSON-like syntax
                } else {
                    print "Line " NR ": JSON syntax in " block_lang " block: " $0
                    found = 1
                }
            }
        }
        END { exit found ? 1 : 0 }
    ' "$file" || true)
    
    if [ $? -eq 1 ]; then
        echo "❌ ERROR: Mixed syntax detected:"
        echo "$MIXED_SYNTAX"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        echo "✅ No mixed syntax in code blocks"
    fi
    
    # Check 4: Broken file paths
    BROKEN_PATHS=$(grep -n "android -test - client" "$file" || true)
    if [ -n "$BROKEN_PATHS" ]; then
        echo "❌ ERROR: Broken file paths found:"
        echo "$BROKEN_PATHS"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        echo "✅ No broken file paths"
    fi
    
    # Check 5: Invalid Gradle syntax in wrong code blocks
    GRADLE_IN_KOTLIN=$(awk '
        /^```kotlin/ { in_kotlin = 1; next }
        /^```$/ { in_kotlin = 0; next }
        in_kotlin && /implementation ['\''"]/ {
            print "Line " NR ": Gradle syntax in kotlin block: " $0
            found = 1
        }
        END { exit found ? 1 : 0 }
    ' "$file" || true)
    
    if [ $? -eq 1 ]; then
        echo "❌ ERROR: Gradle syntax in Kotlin blocks:"
        echo "$GRADLE_IN_KOTLIN"  
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        echo "✅ No Gradle syntax in Kotlin blocks"
    fi
    
    # Check 6: JSON comments (not allowed in JSON standard)
    JSON_COMMENTS=$(awk '
        /^```json/ { in_json = 1; next }
        /^```$/ { in_json = 0; next }
        in_json && /\/\/.*/ {
            print "Line " NR ": JSON comment found: " $0
            found = 1
        }
        END { exit found ? 1 : 0 }
    ' "$file" || true)
    
    if [ $? -eq 1 ]; then
        echo "❌ ERROR: JSON comments found (not allowed in JSON standard):"
        echo "$JSON_COMMENTS"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        echo "✅ No JSON comments"
    fi
    
    # Check 7: Import statements in Kotlin code blocks
    KOTLIN_IMPORTS=$(awk '
        /^```kotlin/ { in_kotlin = 1; next }
        /^```$/ { in_kotlin = 0; next }
        in_kotlin && /^import / {
            print "Line " NR ": Import statement in kotlin block: " $0
            found = 1
        }
        END { exit found ? 1 : 0 }
    ' "$file" || true)
    
    if [ $? -eq 1 ]; then
        echo "❌ ERROR: Import statements found in Kotlin blocks:"
        echo "$KOTLIN_IMPORTS"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        echo "✅ No import statements in Kotlin blocks"
    fi
    
    # Check 8: Invalid syntax in code blocks (incomplete statements)
    INVALID_SYNTAX=$(awk '
        /^```(kotlin|java|javascript|typescript)/ { 
            lang = substr($0, 4)
            in_code = 1
            next 
        }
        /^```$/ { in_code = 0; next }
        in_code {
            # Check for method calls starting with dot (incomplete)
            if (/^\s*\./) {
                print "Line " NR ": Incomplete method call in " lang " block: " $0
                found = 1
            }
            # Check for unmatched braces/parentheses on single lines
            if (/^\s*\)/ || /^\s*\}/ || /^\s*\]/) {
                print "Line " NR ": Unmatched closing bracket in " lang " block: " $0
                found = 1
            }
        }
        END { exit found ? 1 : 0 }
    ' "$file" || true)
    
    if [ $? -eq 1 ]; then
        echo "❌ ERROR: Invalid syntax in code blocks:"
        echo "$INVALID_SYNTAX"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        echo "✅ No invalid syntax in code blocks"
    fi
done

echo ""
echo "📊 Validation Summary:"
echo "Files checked: $TOTAL_FILES"
echo "Errors found: $ERROR_COUNT"

if [ $ERROR_COUNT -eq 0 ]; then
    echo "🎉 All markdown files are valid!"
    exit 0
else
    echo "💥 Found $ERROR_COUNT error(s) across $TOTAL_FILES file(s)"
    exit 1
fi