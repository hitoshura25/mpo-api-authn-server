#!/usr/bin/env python3
"""
URL-to-Code Endpoint Mapping

Maps URL-based vulnerability findings (from DAST/ZAP scans) to actual source code route handlers 
for enhanced context extraction.

This module provides the ability to:
1. Discover route patterns in Kotlin/Ktor and TypeScript/Express applications
2. Map vulnerability URLs to actual code route handlers  
3. Extract route handler context for enhanced training data

Usage:
    from url_to_code_mapper import URLToCodeMapper
    
    mapper = URLToCodeMapper(project_root)
    route_mapping = mapper.find_route_handler("http://localhost:8080/health")
    
    if route_mapping:
        print(f"URL maps to: {route_mapping['file_path']}:{route_mapping['line_number']}")
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse


class URLToCodeMapper:
    """Maps vulnerability URLs to actual source code route handlers."""
    
    def __init__(self, project_root: Path):
        """
        Initialize URL-to-code mapper.
        
        Args:
            project_root: Root directory of the project to scan for routes
        """
        self.project_root = Path(project_root)
        self.route_cache = {}  # Cache discovered routes for performance
        self.route_patterns = self._discover_route_patterns()
        
        print(f"🗺️ URL-to-Code Mapper initialized for project: {self.project_root}")
        print(f"   Discovered {len(self.route_patterns)} route patterns")
    
    def _discover_route_patterns(self) -> List[Dict[str, Any]]:
        """Discover all route definitions in the codebase."""
        
        route_patterns = []
        
        # Kotlin/Ktor route patterns
        print("🔍 Discovering Kotlin/Ktor routes...")
        kotlin_routes = self._find_kotlin_routes()
        route_patterns.extend(kotlin_routes)
        print(f"   Found {len(kotlin_routes)} Kotlin routes")
        
        # TypeScript/Express route patterns (for web-test-client)
        print("🔍 Discovering TypeScript/Express routes...")
        typescript_routes = self._find_typescript_routes()
        route_patterns.extend(typescript_routes)
        print(f"   Found {len(typescript_routes)} TypeScript routes")
        
        return route_patterns
    
    def _find_kotlin_routes(self) -> List[Dict[str, Any]]:
        """Find Ktor route definitions in Kotlin files."""
        
        kotlin_routes = []
        kotlin_files = list(self.project_root.rglob("**/*.kt"))
        
        # Ktor route patterns: get("/path"), post("/path"), etc.
        route_pattern = re.compile(r'(get|post|put|delete|patch)\s*\(\s*"([^"]+)"\s*\)')
        
        for kotlin_file in kotlin_files:
            try:
                content = kotlin_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    matches = route_pattern.findall(line.strip())
                    for method, path in matches:
                        kotlin_routes.append({
                            'method': method.upper(),
                            'path': path,
                            'file_path': str(kotlin_file),
                            'line_number': line_num,
                            'handler_type': 'kotlin_ktor',
                            'route_definition': line.strip()
                        })
                        
            except (UnicodeDecodeError, OSError):
                continue  # Skip files that can't be read
                
        return kotlin_routes
    
    def _find_typescript_routes(self) -> List[Dict[str, Any]]:
        """Find Express/Node.js route definitions in TypeScript files."""
        
        typescript_routes = []
        ts_files = list(self.project_root.rglob("**/*.ts"))
        
        # Express route patterns: app.get("/path"), router.post("/path"), etc.
        route_pattern = re.compile(r'(app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']\s*,')
        
        for ts_file in ts_files:
            try:
                content = ts_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    matches = route_pattern.findall(line.strip())
                    for router_type, method, path in matches:
                        typescript_routes.append({
                            'method': method.upper(),
                            'path': path,
                            'file_path': str(ts_file),
                            'line_number': line_num,
                            'handler_type': 'typescript_express',
                            'route_definition': line.strip()
                        })
                        
            except (UnicodeDecodeError, OSError):
                continue  # Skip files that can't be read
                
        return typescript_routes
    
    def find_route_handler(self, vulnerability_url: str) -> Optional[Dict[str, Any]]:
        """Map vulnerability URL to actual code route handler."""
        
        # Parse URL to extract path
        parsed_url = urlparse(vulnerability_url)
        target_path = parsed_url.path or "/"
        
        print(f"🎯 Mapping URL '{vulnerability_url}' to route handler...")
        print(f"   Extracted path: '{target_path}'")
        
        # Find matching route patterns
        matching_routes = []
        for route in self.route_patterns:
            if self._path_matches(route['path'], target_path):
                matching_routes.append(route)
        
        if not matching_routes:
            print(f"   ❌ No matching routes found for path: {target_path}")
            return None
        
        # Prefer exact matches over pattern matches
        exact_matches = [r for r in matching_routes if r['path'] == target_path]
        if exact_matches:
            best_match = exact_matches[0]
            print(f"   ✅ Exact match found: {best_match['file_path']}:{best_match['line_number']}")
            return best_match
        
        # Return best pattern match (shortest path wins for specificity)
        best_match = min(matching_routes, key=lambda r: len(r['path']))
        print(f"   ✅ Pattern match found: {best_match['file_path']}:{best_match['line_number']}")
        return best_match
    
    def _path_matches(self, route_path: str, target_path: str) -> bool:
        """Check if route path matches target path (handles path parameters)."""
        
        # Exact match
        if route_path == target_path:
            return True
        
        # Handle path parameters: /user/{id} matches /user/123
        pattern = re.escape(route_path).replace(r'\{[^}]+\}', r'[^/]+')
        return bool(re.fullmatch(pattern, target_path))
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """Get statistics about discovered routes."""
        
        stats = {
            'total_routes': len(self.route_patterns),
            'kotlin_routes': len([r for r in self.route_patterns if r['handler_type'] == 'kotlin_ktor']),
            'typescript_routes': len([r for r in self.route_patterns if r['handler_type'] == 'typescript_express']),
            'methods': {},
            'file_coverage': set()
        }
        
        for route in self.route_patterns:
            method = route['method']
            stats['methods'][method] = stats['methods'].get(method, 0) + 1
            stats['file_coverage'].add(route['file_path'])
        
        stats['file_coverage'] = len(stats['file_coverage'])
        
        return stats
    
    def print_route_discovery_summary(self):
        """Print summary of route discovery results."""
        
        stats = self.get_route_statistics()
        
        print("\n📊 Route Discovery Summary:")
        print("=" * 40)
        print(f"Total Routes Found: {stats['total_routes']}")
        print(f"Kotlin/Ktor Routes: {stats['kotlin_routes']}")
        print(f"TypeScript/Express Routes: {stats['typescript_routes']}")
        print(f"Files Covered: {stats['file_coverage']}")
        
        if stats['methods']:
            print("\nHTTP Methods Distribution:")
            for method, count in sorted(stats['methods'].items()):
                print(f"  {method}: {count}")
        
        print("=" * 40)


def enhance_vulnerability_with_url_mapping(vulnerability: Dict[str, Any], 
                                           url_mapper: URLToCodeMapper) -> bool:
    """
    Enhance URL-based vulnerabilities with code context.
    
    Args:
        vulnerability: Vulnerability dictionary to enhance
        url_mapper: URLToCodeMapper instance for route discovery
        
    Returns:
        bool: True if successfully mapped, False otherwise
    """
    
    if vulnerability.get('url') and not vulnerability.get('file_path'):
        route_mapping = url_mapper.find_route_handler(vulnerability['url'])
        
        if route_mapping:
            # Add route handler context to vulnerability
            vulnerability['file_path'] = route_mapping['file_path']
            vulnerability['line_number'] = route_mapping['line_number']
            vulnerability['handler_type'] = route_mapping['handler_type']
            vulnerability['route_definition'] = route_mapping['route_definition']
            vulnerability['method'] = route_mapping['method']
            
            # Add route-specific metadata
            vulnerability['endpoint_metadata'] = {
                'endpoint_type': route_mapping['handler_type'],
                'http_method': route_mapping['method'],
                'route_pattern': route_mapping['path'],
                'mapped_from_url': vulnerability['url']
            }
            
            print(f"✅ Enhanced vulnerability with URL mapping:")
            print(f"   URL: {vulnerability['url']}")
            print(f"   → {vulnerability['file_path']}:{vulnerability['line_number']}")
            
            return True  # Successfully mapped
    
    return False  # No mapping available


def test_url_mapping():
    """Test URL mapping with sample data."""
    
    print("\n🧪 Testing URL-to-code mapping...")
    
    # Initialize mapper with current project
    project_root = Path(__file__).parent.parent
    mapper = URLToCodeMapper(project_root)
    
    # Print route discovery summary
    mapper.print_route_discovery_summary()
    
    # Test sample URLs
    test_urls = [
        "http://localhost:8080/",
        "http://localhost:8080/health",
        "http://localhost:8080/metrics", 
        "http://localhost:8082/login",
        "http://localhost:8082/register"
    ]
    
    print("\n🎯 Testing URL mappings:")
    print("-" * 40)
    
    for url in test_urls:
        result = mapper.find_route_handler(url)
        if result:
            print(f"✅ {url}")
            print(f"   → {result['file_path']}:{result['line_number']}")
            print(f"   → {result['handler_type']} {result['method']} handler")
        else:
            print(f"❌ {url} - No mapping found")
        print()


if __name__ == "__main__":
    test_url_mapping()