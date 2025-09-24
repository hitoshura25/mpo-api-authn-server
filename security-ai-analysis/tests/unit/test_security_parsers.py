"""
Comprehensive unit tests for all security parsers
Tests each parser function directly with controlled test data
"""
import os
import sys
import pytest
from pathlib import Path

# Add parent directory to path so we can import parsers
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from parsers.semgrep_parser import parse_semgrep_sarif
from parsers.trivy_parser import parse_trivy_json
from parsers.checkov_parser import parse_checkov_json
from parsers.osv_parser import parse_osv_json
from parsers.zap_parser import parse_zap_json


class TestSecurityParsers:
    """Test all security parsers with controlled test data"""

    @classmethod
    def setup_class(cls):
        """Set up test data directory path"""
        cls.test_data_dir = Path(__file__).parent.parent / "fixtures" / "controlled_test_data"

        # Verify all test files exist
        required_files = [
            "semgrep.sarif",
            "trivy-results.sarif",
            "checkov-results.sarif",
            "osv-results.json",
            "zap-report.json"
        ]

        for filename in required_files:
            file_path = cls.test_data_dir / filename
            assert file_path.exists(), f"Required test file missing: {file_path}"

    def test_semgrep_parser_exact_count(self):
        """Test Semgrep parser finds exactly 3 vulnerabilities with correct details"""
        file_path = str(self.test_data_dir / "semgrep.sarif")
        results = parse_semgrep_sarif(file_path)

        # Exact count assertion
        assert len(results) == 3, f"Expected 3 vulnerabilities, got {len(results)}"

        # Verify all results have required fields
        for result in results:
            assert 'tool' in result
            assert 'id' in result
            assert 'severity' in result
            assert 'file_path' in result
            assert 'start' in result
            assert 'line' in result['start']
            assert result['tool'] == 'semgrep'

        # Test specific vulnerability details
        rule_ids = [r['id'] for r in results]
        expected_rule_ids = ['test.hardcoded-password', 'test.sql-injection', 'test.xss-vulnerability']
        assert sorted(rule_ids) == sorted(expected_rule_ids), f"Expected {expected_rule_ids}, got {rule_ids}"

        # Test specific details for first vulnerability
        hardcoded_pass = next(r for r in results if r['id'] == 'test.hardcoded-password')
        assert hardcoded_pass['file_path'] == 'test-config.js'
        assert hardcoded_pass['severity'] == 'HIGH'
        assert hardcoded_pass['start']['line'] == 15
        assert 'CWE-798' in str(hardcoded_pass.get('cwe', []))

    def test_trivy_parser_exact_count(self):
        """Test Trivy parser finds exactly 2 vulnerabilities with correct details"""
        file_path = str(self.test_data_dir / "trivy-results.sarif")
        results = parse_trivy_json(file_path)

        # Exact count assertion
        assert len(results) == 2, f"Expected 2 vulnerabilities, got {len(results)}"

        # Verify all results have required fields
        for result in results:
            assert 'tool' in result
            assert 'id' in result
            assert 'severity' in result
            assert 'package' in result
            assert 'path' in result
            assert result['tool'] == 'trivy'

        # Test specific vulnerability details
        vuln_ids = [r['id'] for r in results]
        expected_vuln_ids = ['CVE-2024-0001', 'CVE-2024-0002']
        assert sorted(vuln_ids) == sorted(expected_vuln_ids), f"Expected {expected_vuln_ids}, got {vuln_ids}"

        # Test specific details for lodash vulnerability
        lodash_vuln = next(r for r in results if r['id'] == 'CVE-2024-0001')
        assert lodash_vuln['package'] == 'lodash'
        assert lodash_vuln['severity'] == 'HIGH'
        assert lodash_vuln['path'] == 'package-lock.json'
        assert lodash_vuln['fixed_version'] == '4.17.21'

    def test_checkov_parser_exact_count(self):
        """Test Checkov parser finds exactly 1 vulnerability with correct details"""
        file_path = str(self.test_data_dir / "checkov-results.sarif")
        results = parse_checkov_json(file_path)

        # Exact count assertion
        assert len(results) == 1, f"Expected 1 vulnerability, got {len(results)}"

        result = results[0]

        # Verify required fields
        assert result['tool'] == 'checkov'
        assert result['id'] == 'CKV_AWS_20'
        assert result['path'] == 'terraform/s3.tf'
        assert result['start']['line'] == 15
        assert result['resource'] == 'aws_s3_bucket.test_bucket'
        assert 'S3 Bucket has an insecure ACL' in result['description']

    def test_osv_parser_exact_count(self):
        """Test OSV Scanner parser finds exactly 1 vulnerability with correct details"""
        file_path = str(self.test_data_dir / "osv-results.json")
        results = parse_osv_json(file_path)

        # Exact count assertion
        assert len(results) == 1, f"Expected 1 vulnerability, got {len(results)}"

        result = results[0]

        # Verify required fields
        assert result['tool'] == 'osv-scanner'
        assert result['id'] == 'GHSA-j8r2-6x86-q33q'
        assert result['package_name'] == 'requests'
        assert result['ecosystem'] == 'PyPI'
        assert result['path'] == 'requirements.txt'
        assert result['start']['line'] == 1  # OSV uses synthetic line numbers
        assert 'proxy authentication' in result['summary']

    def test_zap_parser_exact_count(self):
        """Test ZAP parser finds exactly 1 vulnerability with correct details"""
        file_path = str(self.test_data_dir / "zap-report.json")
        results = parse_zap_json(file_path)

        # Exact count assertion
        assert len(results) == 1, f"Expected 1 vulnerability, got {len(results)}"

        result = results[0]

        # Verify required fields
        assert result['tool'] == 'zap'
        assert result['id'] == '10035'
        assert result['severity'] == 'LOW'  # Risk code 1 maps to LOW
        assert result['site_host'] == 'localhost'
        assert result['site_port'] == '8080'
        assert result['path'] == 'http://localhost:8080/'
        assert 'Strict-Transport-Security' in result['name']

    def test_parsers_handle_missing_files_gracefully(self):
        """Test that all parsers handle missing/non-existent files gracefully by returning empty lists"""
        # This test verifies that parsers don't crash when given non-existent file paths

        # Test with non-existent file (should return empty list, not crash)
        results = parse_semgrep_sarif("/nonexistent/file.sarif")
        assert results == [], "Parser should return empty list for missing file"

        results = parse_trivy_json("/nonexistent/file.json")
        assert results == [], "Parser should return empty list for missing file"

        results = parse_checkov_json("/nonexistent/file.json")
        assert results == [], "Parser should return empty list for missing file"

        results = parse_osv_json("/nonexistent/file.json")
        assert results == [], "Parser should return empty list for missing file"

        results = parse_zap_json("/nonexistent/file.json")
        assert results == [], "Parser should return empty list for missing file"

    def test_all_parsers_total_count(self):
        """Integration test: verify all parsers together find exactly 8 vulnerabilities"""
        semgrep_results = parse_semgrep_sarif(str(self.test_data_dir / "semgrep.sarif"))
        trivy_results = parse_trivy_json(str(self.test_data_dir / "trivy-results.sarif"))
        checkov_results = parse_checkov_json(str(self.test_data_dir / "checkov-results.sarif"))
        osv_results = parse_osv_json(str(self.test_data_dir / "osv-results.json"))
        zap_results = parse_zap_json(str(self.test_data_dir / "zap-report.json"))

        total_count = (
            len(semgrep_results) +
            len(trivy_results) +
            len(checkov_results) +
            len(osv_results) +
            len(zap_results)
        )

        # Exact total assertion - critical for integration tests
        assert total_count == 8, f"Expected total of 8 vulnerabilities across all parsers, got {total_count}"

        # Verify breakdown matches expected
        expected_counts = {
            'semgrep': 3,
            'trivy': 2,
            'checkov': 1,
            'osv-scanner': 1,
            'zap': 1
        }

        actual_counts = {
            'semgrep': len(semgrep_results),
            'trivy': len(trivy_results),
            'checkov': len(checkov_results),
            'osv-scanner': len(osv_results),
            'zap': len(zap_results)
        }

        assert actual_counts == expected_counts, f"Tool breakdown mismatch. Expected: {expected_counts}, Got: {actual_counts}"

    def test_parser_field_consistency(self):
        """Test that all parsers return consistent field structures for enhanced dataset compatibility"""
        semgrep_results = parse_semgrep_sarif(str(self.test_data_dir / "semgrep.sarif"))
        trivy_results = parse_trivy_json(str(self.test_data_dir / "trivy-results.sarif"))
        checkov_results = parse_checkov_json(str(self.test_data_dir / "checkov-results.sarif"))
        osv_results = parse_osv_json(str(self.test_data_dir / "osv-results.json"))
        zap_results = parse_zap_json(str(self.test_data_dir / "zap-report.json"))

        all_results = semgrep_results + trivy_results + checkov_results + osv_results + zap_results

        # Verify all results have required fields for enhanced dataset creation
        required_fields = ['tool', 'path', 'start']

        for i, result in enumerate(all_results):
            for field in required_fields:
                assert field in result, f"Result {i} from tool {result.get('tool', 'unknown')} missing required field: {field}"

            # Verify start field has line number
            assert 'line' in result['start'], f"Result {i} missing start.line field"
            assert isinstance(result['start']['line'], int), f"Result {i} start.line is not an integer"
            assert result['start']['line'] >= 1, f"Result {i} start.line must be >= 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])