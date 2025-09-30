#!/usr/bin/env python3
"""
Vulnerable Code Extractor for AI Security Enhancement

This module extracts code context from vulnerability data to enable
code-aware security analysis and fix generation.

Classes:
- VulnerableCodeExtractor: Main class for extracting code context from vulnerabilities
- CodeContext: Data class representing extracted code context
- ContextExtractionResult: Result of context extraction with metadata

Usage:
    extractor = VulnerableCodeExtractor()
    context = extractor.extract_vulnerability_context(vulnerability_data)
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass, field


@dataclass
class CodeContext:
    """
    Represents extracted code context around a vulnerability.
    """
    file_path: str
    vulnerability_line: int
    vulnerability_column: Optional[int]
    
    # Code snippets
    vulnerable_code: str  # The specific vulnerable code
    function_context: Optional[str]  # Surrounding function
    class_context: Optional[str]  # Surrounding class if applicable
    
    # Context lines
    before_lines: List[str] = field(default_factory=list)
    after_lines: List[str] = field(default_factory=list)
    
    # Function information
    function_name: Optional[str] = None
    function_start_line: Optional[int] = None
    function_end_line: Optional[int] = None
    
    # Class information
    class_name: Optional[str] = None
    class_start_line: Optional[int] = None
    
    # File metadata
    file_extension: Optional[str] = None
    language: Optional[str] = None
    
    def get_full_context(self, line_padding: int = 5) -> str:
        """Get complete code context as formatted string."""
        lines = []
        
        if self.class_context:
            lines.append(f"// Class: {self.class_name}")
            lines.append(self.class_context)
            lines.append("")
        
        if self.function_context:
            lines.append(f"// Function: {self.function_name}")
            lines.append(self.function_context)
            lines.append("")
        
        lines.append(f"// Vulnerable code at line {self.vulnerability_line}:")
        
        # Add context lines with line numbers
        start_line = max(1, self.vulnerability_line - line_padding)
        for i, line in enumerate(self.before_lines[-line_padding:]):
            line_num = start_line + i
            prefix = ">>> " if line_num == self.vulnerability_line else "    "
            lines.append(f"{prefix}{line_num:4d}: {line}")
        
        return "\n".join(lines)


@dataclass
class ContextExtractionResult:
    """
    Result of vulnerability context extraction.
    """
    success: bool
    code_context: Optional[CodeContext]
    error_message: Optional[str] = None
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)


class VulnerableCodeExtractor:
    """
    Extracts code context from vulnerability reports for enhanced analysis.
    
    This class handles different vulnerability report formats and extracts
    surrounding code context to enable more specific security analysis.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the code extractor.
        
        Args:
            project_root: Root directory of the project. If None, auto-detects.
        """
        self.project_root = project_root or self._detect_project_root()
        
        # Language detection mappings
        self.language_map = {
            '.kt': 'kotlin',
            '.java': 'java', 
            '.js': 'javascript',
            '.ts': 'typescript',
            '.py': 'python',
            '.html': 'html',
            '.xml': 'xml',
            '.gradle': 'gradle',
            '.kts': 'kotlin',
            '.cjs': 'javascript',
            # Infrastructure file types
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.lockfile': 'gradle-lockfile',
            '.toml': 'toml',
            '.dockerfile': 'dockerfile',
            '.dockerignore': 'dockerfile',
            '.gitignore': 'gitignore',
            '.md': 'markdown',
            '.properties': 'properties',
            '.conf': 'config',
            '.cfg': 'config',
            '.ini': 'ini'
        }
        
        # Function detection patterns by language
        self.function_patterns = {
            'kotlin': [
                r'^(\s*)(?:public|private|internal|protected)?\s*(?:suspend\s+)?fun\s+(\w+)\s*\(',
                r'^(\s*)(?:public|private|internal|protected)?\s*(?:inline\s+)?fun\s+(\w+)\s*\(',
            ],
            'java': [
                r'^(\s*)(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)*(\w+)\s*\(',
            ],
            'javascript': [
                r'^(\s*)(?:function\s+(\w+)\s*\(|(\w+)\s*:\s*function\s*\(|(\w+)\s*=\s*function\s*\()',
                r'^(\s*)(?:const|let|var)\s+(\w+)\s*=\s*\(',
                r'^(\s*)(\w+)\s*\(\s*\)\s*\{',  # Arrow functions
            ],
            'typescript': [
                r'^(\s*)(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(',
                r'^(\s*)(?:public|private|protected)?\s*(\w+)\s*\(',
                r'^(\s*)(?:const|let)\s+(\w+)\s*:\s*\(',
            ],
            'python': [
                r'^(\s*)def\s+(\w+)\s*\(',
                r'^(\s*)async\s+def\s+(\w+)\s*\(',
            ]
        }
        
        # Class detection patterns by language
        self.class_patterns = {
            'kotlin': [r'^(\s*)(?:public|private|internal)?\s*(?:data\s+|sealed\s+)?class\s+(\w+)'],
            'java': [r'^(\s*)(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)'],
            'javascript': [r'^(\s*)class\s+(\w+)'],
            'typescript': [r'^(\s*)(?:export\s+)?(?:abstract\s+)?class\s+(\w+)'],
            'python': [r'^(\s*)class\s+(\w+)']
        }
    
    def _detect_project_root(self) -> Path:
        """Auto-detect project root directory."""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / '.git').exists() or (current / 'build.gradle.kts').exists():
                return current  # Return the directory containing .git or build.gradle.kts
            current = current.parent
        return Path.cwd()
    
    def extract_vulnerability_context(self, vulnerability: Dict[str, Any]) -> ContextExtractionResult:
        """
        Extract code context from a vulnerability report.
        
        Args:
            vulnerability: Vulnerability data from security tools
            
        Returns:
            ContextExtractionResult with extracted code context
        """
        try:
            # Extract basic vulnerability info
            # Check for both 'path' (standard) and 'file_path' (URL-mapped) fields
            file_path = vulnerability.get('file_path') or vulnerability.get('path', '')
            start_info = vulnerability.get('start', {})
            tool_name = vulnerability.get('tool', 'unknown')
            
            # For URL-mapped vulnerabilities, use line_number if available
            if vulnerability.get('line_number') and not start_info.get('line'):
                start_info = {'line': vulnerability.get('line_number')}
            
            # Intelligent file search - find actual file regardless of path format
            if file_path:
                actual_file_path = self._find_actual_file(file_path)
                if actual_file_path:
                    file_path = str(actual_file_path)
                else:
                    # Infrastructure vulnerability - no source file available for code context
                    # Return success but with no code context (infrastructure vulnerabilities are still valuable)
                    return ContextExtractionResult(
                        success=True,
                        code_context=None,
                        error_message=None,
                        extraction_metadata={
                            'extraction_type': 'infrastructure',
                            'original_path': file_path,
                            'reason': 'Infrastructure vulnerability - no source code context available'
                        }
                    )
            
            if not file_path or not start_info:
                return ContextExtractionResult(
                    success=False,
                    code_context=None,
                    error_message="Missing file path or start location information"
                )
            
            line_num = start_info.get('line')
            col_num = start_info.get('col')
            
            if not line_num:
                return ContextExtractionResult(
                    success=False,
                    code_context=None,
                    error_message="Missing line number information"
                )
            
            # Resolve absolute file path
            abs_file_path = self._resolve_file_path(file_path)
            if not abs_file_path.exists():
                return ContextExtractionResult(
                    success=False,
                    code_context=None,
                    error_message=f"File not found: {abs_file_path}"
                )
            
            # Read file content
            try:
                with open(abs_file_path, 'r', encoding='utf-8') as f:
                    file_lines = f.readlines()
            except Exception as e:
                return ContextExtractionResult(
                    success=False,
                    code_context=None,
                    error_message=f"Failed to read file: {e}"
                )
            
            # Extract code context
            code_context = self._extract_code_context(
                file_lines=file_lines,
                file_path=file_path,
                line_num=line_num,
                col_num=col_num,
                abs_file_path=abs_file_path
            )
            
            return ContextExtractionResult(
                success=True,
                code_context=code_context,
                extraction_metadata={
                    'total_lines': len(file_lines),
                    'file_size_bytes': abs_file_path.stat().st_size,
                    'extraction_method': 'static_analysis'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            raise
    
    def _find_actual_file(self, scan_file_path: str) -> Path:
        """
        Intelligently find the actual file in the project regardless of scan path format.
        
        This method now gracefully handles infrastructure vulnerabilities by skipping
        paths that don't correspond to source files while still allowing the vulnerability
        to be processed (just without code context extraction).
        
        Args:
            scan_file_path: File path from security scan data (may be CI path, absolute, relative, etc.)
            
        Returns:
            Actual file path if found, None otherwise (indicates infrastructure/non-source vulnerability)
        """
        if not scan_file_path:
            return None
            
        # Skip URL references - these are not actual files
        if any(scan_file_path.lower().startswith(protocol) for protocol in ['http:', 'https:', 'ftp:', 'file:']):
            return None
            
        # Skip paths with URL protocols in the middle
        if any(f'/{protocol}' in scan_file_path.lower() for protocol in ['http:', 'https:', 'ftp:']):
            return None
        
        # Skip container references - these represent runtime containers, not source files
        if scan_file_path.startswith(('container:', 'hitoshura25/', 'library/', 'docker.io/', 'registry.', 'ghcr.io/')):
            return None
        
        # Skip Docker image patterns - these are infrastructure, not source code
        # Patterns like "nginx:alpine", "postgres:15", "node:18", etc.
        if ':' in scan_file_path and '/' not in scan_file_path and not scan_file_path.startswith('.'):
            return None
        
        # Skip Docker-style image references with registry prefixes
        # Patterns like "hitoshura25/webauthn-server:latest", "docker.io/library/postgres:15"
        if '/' in scan_file_path and ':' in scan_file_path:
            parts = scan_file_path.split('/')
            if len(parts) >= 2 and ':' in parts[-1]:  # Last part contains version/tag
                return None
        
        # Skip common build artifacts and runtime files
        if any(scan_file_path.endswith(suffix) for suffix in ['.jar', '.war', '.ear', '.class']):
            return None
        
        # Skip common non-source directories when they appear as bare names
        if scan_file_path in ['webauthn-server', 'webauthn-test-credentials-service', 'android-test-client']:
            return None
            
        # Skip temporary directories and build outputs
        if any(part in scan_file_path.lower() for part in ['/tmp/', '/temp/', '/build/', '/target/', '/dist/', '/node_modules/']):
            return None
        
        # Skip paths that look like package names or dependencies
        # e.g., "org.apache.commons", "com.google.guava:guava"
        if '.' in scan_file_path and not '/' in scan_file_path:
            parts = scan_file_path.split('.')
            if len(parts) >= 3 and all(part.isalnum() for part in parts[:3]):  # Looks like package name
                return None
        
        # Skip Maven-style coordinates (groupId:artifactId:version)
        if scan_file_path.count(':') >= 2:
            return None
        
        # Extract meaningful path components
        path_candidates = self._extract_path_candidates(scan_file_path)
        
        # Search for the file using multiple strategies
        for candidate in path_candidates:
            found_path = self._search_for_file(candidate)
            if found_path:
                return found_path
                
        return None
    
    def _extract_path_candidates(self, scan_path: str) -> list:
        """Extract potential file path candidates from scan data."""
        candidates = []
        
        # Strategy 1: Extract relative path from CI environment paths
        # e.g., "/home/runner/work/project/project/android-test-client/app/gradle.lockfile"
        # -> "android-test-client/app/gradle.lockfile"
        if '/runner/work/' in scan_path:
            parts = scan_path.split('/runner/work/')[-1].split('/')
            if len(parts) >= 3:  # [project, project, ...actual_path]
                candidates.append('/'.join(parts[2:]))  # Skip duplicate project names
        
        # Strategy 2: Fix GitHub workflow paths
        # e.g., "/path/github/workflows/file.yml" -> ".github/workflows/file.yml"
        if '/github/workflows/' in scan_path:
            workflow_file = scan_path.split('/github/workflows/')[-1]
            candidates.append(f".github/workflows/{workflow_file}")
        
        if scan_path.startswith('github/workflows/'):
            candidates.append(f".{scan_path}")
        
        # Strategy 3: Use the path as-is if it looks relative
        if not scan_path.startswith('/'):
            candidates.append(scan_path)
        
        # Strategy 4: Extract just the filename for broader search
        filename = Path(scan_path).name
        if filename:
            candidates.append(filename)
        
        # Strategy 5: Extract potential relative paths from absolute paths
        # Try different depth levels
        path_parts = scan_path.split('/')
        for i in range(1, min(len(path_parts), 4)):  # Try up to 3 levels deep
            if len(path_parts) > i:
                candidates.append('/'.join(path_parts[-i:]))
        
        return candidates
    
    def _search_for_file(self, relative_path: str) -> Path:
        """Search for a file using various strategies."""
        if not relative_path:
            return None
        
        search_locations = [
            self.project_root,  # Current project root
            self.project_root.parent,  # Parent directory (for sibling projects)
        ]
        
        filename = Path(relative_path).name
        
        for base_location in search_locations:
            # Strategy 1: Direct path match
            direct_path = base_location / relative_path
            if direct_path.exists():
                return direct_path
            
            # Strategy 2: Find by filename using glob search
            try:
                matches = list(base_location.glob(f"**/{filename}"))
                if matches:
                    # If multiple matches, prefer ones that match more of the original path
                    best_match = self._find_best_path_match(matches, relative_path)
                    if best_match:
                        return best_match
            except Exception as e:
                self.logger.error(f"Error during glob search: {e}")
                raise
        
        return None
    
    def _find_best_path_match(self, candidates: list, target_path: str) -> Path:
        """Find the best matching path from candidates."""
        if len(candidates) == 1:
            return candidates[0]
        
        target_parts = target_path.lower().split('/')
        best_score = -1
        best_match = None
        
        for candidate in candidates:
            # Score based on how many path components match
            candidate_parts = str(candidate).lower().split('/')
            score = 0
            for target_part in target_parts:
                if target_part in candidate_parts:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = candidate
        
        return best_match or candidates[0]  # Return best match or first as fallback
    
    def _resolve_file_path(self, file_path: str) -> Path:
        """Resolve file path to absolute path."""
        if not file_path:
            return None
            
        path = Path(file_path)
        
        # If already absolute, return as-is
        if path.is_absolute():
            return path
            
        # Handle relative paths
        clean_path = file_path.strip('./')
        return self.project_root / clean_path
    
    def _extract_code_context(self, file_lines: List[str], file_path: str, 
                            line_num: int, col_num: Optional[int],
                            abs_file_path: Path) -> CodeContext:
        """Extract detailed code context around vulnerability."""
        
        # Detect language
        file_ext = abs_file_path.suffix.lower()
        filename = abs_file_path.name.lower()
        
        # Check for special filenames first
        if filename.endswith('gradle.lockfile'):
            language = 'gradle-lockfile'
        elif filename in ['dockerfile', 'docker-compose.yml', 'docker-compose.yaml']:
            language = 'dockerfile'
        elif filename in ['.gitignore', '.dockerignore']:
            language = 'gitignore'
        elif filename.endswith('.lock'):
            language = 'lockfile'
        else:
            language = self.language_map.get(file_ext, 'unknown')
        
        # Get vulnerable line (1-indexed to 0-indexed)
        vuln_line_idx = line_num - 1
        vulnerable_code = file_lines[vuln_line_idx].rstrip() if vuln_line_idx < len(file_lines) else ""
        
        # Extract context lines
        context_size = 10
        start_idx = max(0, vuln_line_idx - context_size)
        end_idx = min(len(file_lines), vuln_line_idx + context_size + 1)
        
        before_lines = [line.rstrip() for line in file_lines[start_idx:vuln_line_idx]]
        after_lines = [line.rstrip() for line in file_lines[vuln_line_idx + 1:end_idx]]
        
        # Find function context
        function_info = self._find_function_context(file_lines, vuln_line_idx, language)
        
        # Find class context  
        class_info = self._find_class_context(file_lines, vuln_line_idx, language)
        
        return CodeContext(
            file_path=file_path,
            vulnerability_line=line_num,
            vulnerability_column=col_num,
            vulnerable_code=vulnerable_code,
            function_context=function_info.get('code'),
            class_context=class_info.get('code'),
            before_lines=before_lines,
            after_lines=after_lines,
            function_name=function_info.get('name'),
            function_start_line=function_info.get('start_line'),
            function_end_line=function_info.get('end_line'),
            class_name=class_info.get('name'),
            class_start_line=class_info.get('start_line'),
            file_extension=file_ext,
            language=language
        )
    
    def _find_function_context(self, file_lines: List[str], vuln_line_idx: int, language: str) -> Dict[str, Any]:
        """Find the function containing the vulnerable line."""
        if language not in self.function_patterns:
            return {}
        
        patterns = self.function_patterns[language]
        
        # Search backwards for function declaration
        for i in range(vuln_line_idx, -1, -1):
            line = file_lines[i].strip()
            
            for pattern in patterns:
                match = re.search(pattern, file_lines[i])
                if match:
                    # Extract function name from match groups
                    function_name = None
                    for group in match.groups():
                        if group and group.strip() and not group.isspace():
                            if not group.startswith((' ', '\t')):  # Skip indentation groups
                                function_name = group.strip()
                                break
                    
                    if function_name:
                        # Find function end (simple brace matching)
                        func_start = i
                        func_end = self._find_function_end(file_lines, func_start, language)
                        
                        if func_start <= vuln_line_idx <= func_end:
                            function_code = ''.join(file_lines[func_start:func_end + 1])
                            
                            return {
                                'name': function_name,
                                'start_line': func_start + 1,  # Convert to 1-indexed
                                'end_line': func_end + 1,
                                'code': function_code.rstrip()
                            }
        
        return {}
    
    def _find_class_context(self, file_lines: List[str], vuln_line_idx: int, language: str) -> Dict[str, Any]:
        """Find the class containing the vulnerable line."""
        if language not in self.class_patterns:
            return {}
        
        patterns = self.class_patterns[language]
        
        # Search backwards for class declaration
        for i in range(vuln_line_idx, -1, -1):
            for pattern in patterns:
                match = re.search(pattern, file_lines[i])
                if match:
                    # Extract class name
                    class_name = match.groups()[-1]  # Usually last group is class name
                    
                    if class_name:
                        # For class context, just return the class declaration line
                        class_code = file_lines[i].rstrip()
                        
                        return {
                            'name': class_name,
                            'start_line': i + 1,  # Convert to 1-indexed
                            'code': class_code
                        }
        
        return {}
    
    def _find_function_end(self, file_lines: List[str], start_idx: int, language: str) -> int:
        """Find the end of a function using simple brace/indentation matching."""
        if language in ['python']:
            # Python uses indentation
            return self._find_python_function_end(file_lines, start_idx)
        else:
            # Most languages use braces
            return self._find_brace_function_end(file_lines, start_idx)
    
    def _find_python_function_end(self, file_lines: List[str], start_idx: int) -> int:
        """Find end of Python function by indentation."""
        if start_idx >= len(file_lines):
            return start_idx
        
        # Get base indentation
        start_line = file_lines[start_idx]
        base_indent = len(start_line) - len(start_line.lstrip())
        
        for i in range(start_idx + 1, len(file_lines)):
            line = file_lines[i]
            if line.strip():  # Skip empty lines
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= base_indent:
                    return i - 1
        
        return len(file_lines) - 1
    
    def _find_brace_function_end(self, file_lines: List[str], start_idx: int) -> int:
        """Find end of function using brace matching."""
        brace_count = 0
        found_first_brace = False
        
        for i in range(start_idx, len(file_lines)):
            line = file_lines[i]
            
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_first_brace = True
                elif char == '}':
                    brace_count -= 1
                    
                    if found_first_brace and brace_count == 0:
                        return i
        
        return len(file_lines) - 1
    
    def extract_multiple_vulnerabilities(self, vulnerabilities: List[Dict[str, Any]]) -> List[ContextExtractionResult]:
        """
        Extract code context for multiple vulnerabilities.
        
        Args:
            vulnerabilities: List of vulnerability data
            
        Returns:
            List of extraction results
        """
        results = []
        
        for vuln in vulnerabilities:
            result = self.extract_vulnerability_context(vuln)
            results.append(result)
        
        return results
    
    def get_extraction_summary(self, results: List[ContextExtractionResult]) -> Dict[str, Any]:
        """
        Generate summary statistics for extraction results.
        
        Args:
            results: List of extraction results
            
        Returns:
            Summary statistics
        """
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        
        # Group by language
        languages = {}
        files = set()
        
        for result in results:
            if result.success and result.code_context:
                lang = result.code_context.language
                languages[lang] = languages.get(lang, 0) + 1
                files.add(result.code_context.file_path)
        
        return {
            'total_vulnerabilities': total,
            'successful_extractions': successful,
            'failed_extractions': failed,
            'success_rate': successful / total if total > 0 else 0,
            'languages_processed': languages,
            'unique_files': len(files),
            'files_processed': list(files)
        }


# Convenience function for quick usage
def extract_vulnerability_context(vulnerability: Dict[str, Any], 
                                project_root: Optional[Path] = None) -> ContextExtractionResult:
    """
    Quick function to extract context from a single vulnerability.
    
    Args:
        vulnerability: Vulnerability data
        project_root: Project root directory
        
    Returns:
        Extraction result
    """
    extractor = VulnerableCodeExtractor(project_root)
    return extractor.extract_vulnerability_context(vulnerability)