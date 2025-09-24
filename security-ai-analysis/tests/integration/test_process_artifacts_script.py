"""
Comprehensive integration tests for process_artifacts.py pipeline
Tests the complete pipeline from security parsing to dataset creation
"""
import os
import sys
import json
import tempfile
import shutil
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import the main script
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestProcessArtifactsScript:
    """Integration tests for the complete process_artifacts.py pipeline"""

    @classmethod
    def setup_class(cls):
        """Set up test environment"""
        cls.script_path = Path(__file__).parent.parent.parent / "process_artifacts.py"
        cls.test_data_dir = Path(__file__).parent.parent / "fixtures" / "controlled_test_data"

        # Verify script and test data exist
        assert cls.script_path.exists(), f"Script not found: {cls.script_path}"
        assert cls.test_data_dir.exists(), f"Test data directory not found: {cls.test_data_dir}"

    def setup_method(self):
        """Set up for each test"""
        # Create temporary output directory
        self.temp_output_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up after each test"""
        # Remove temporary output directory
        if self.temp_output_dir.exists():
            shutil.rmtree(self.temp_output_dir)

    def run_process_artifacts(self, additional_args=None):
        """
        Helper method to run process_artifacts.py with controlled test data
        Returns CompletedProcess result
        """
        # Base arguments for fast testing (parsing only mode)
        base_args = [
            "python3", str(self.script_path),
            "--artifacts-dir", str(self.test_data_dir),
            "--output-dir", str(self.temp_output_dir),
            "--stop-after", "parsing"  # Fast test mode - stop after parsing phase
        ]

        if additional_args:
            base_args.extend(additional_args)

        # Run the script (without capture_output so user can see progress)
        result = subprocess.run(
            base_args,
            text=True,
            cwd=self.script_path.parent
        )

        return result

    def test_exact_vulnerability_parsing(self):
        """Test that the script parses exactly 8 vulnerabilities from controlled test data"""
        result = self.run_process_artifacts()

        # Script should complete successfully
        assert result.returncode == 0, f"Script failed with return code {result.returncode}"

        # Check that parsing summary file was created
        summary_files = list(self.temp_output_dir.glob("parsing_summary_*.json"))
        assert len(summary_files) >= 1, "No parsing summary file created"

        # Load and verify summary
        with open(summary_files[0], 'r') as f:
            summary = json.load(f)

        # Exact total count assertion
        assert summary["total_analyzed"] == 8, f"Expected 8 total vulnerabilities, got {summary['total_analyzed']}"

        # Exact tool breakdown assertions
        expected_by_tool = {
            "semgrep": 3,
            "sarif-trivy": 2,  # SARIF parser prefixes tool names with 'sarif-'
            "sarif-checkov": 1,  # SARIF parser prefixes tool names with 'sarif-'
            "osv-scanner": 1,
            "zap": 1
        }

        actual_by_tool = summary.get("by_tool", {})
        for tool, expected_count in expected_by_tool.items():
            actual_count = actual_by_tool.get(tool, 0)
            assert actual_count == expected_count, f"Tool {tool}: expected {expected_count}, got {actual_count}"

    def test_tool_specific_parsing_accuracy(self):
        """Test that each tool finds its expected vulnerabilities with correct details"""
        result = self.run_process_artifacts()
        assert result.returncode == 0, f"Script failed with return code {result.returncode}"

        # Load parsed results to check individual vulnerabilities
        results_files = list(self.temp_output_dir.glob("parsed_vulnerabilities_*.json"))
        assert len(results_files) >= 1, "No parsed vulnerabilities file created"

        with open(results_files[0], 'r') as f:
            results = json.load(f)

        # Group results by tool (with debug info)
        by_tool = {}
        print(f"DEBUG: Total results found: {len(results)}")
        for i, result in enumerate(results):
            tool = result.get('tool', 'unknown')
            print(f"DEBUG: Result {i+1}: tool='{tool}', keys={list(result.keys())}")
            if tool not in by_tool:
                by_tool[tool] = []
            by_tool[tool].append(result)

        print(f"DEBUG: Final grouping: {[(k, len(v)) for k, v in by_tool.items()]}")

        # Verify Semgrep findings
        semgrep_results = by_tool.get('semgrep', [])
        assert len(semgrep_results) == 3, f"Expected 3 Semgrep results, got {len(semgrep_results)}"

        semgrep_rule_ids = [r.get('id') for r in semgrep_results]
        expected_semgrep_ids = ['test.hardcoded-password', 'test.sql-injection', 'test.xss-vulnerability']
        assert set(semgrep_rule_ids) == set(expected_semgrep_ids), f"Semgrep rule IDs mismatch"

        # Verify Trivy findings (SARIF parser uses 'sarif-trivy' as tool name)
        trivy_results = by_tool.get('sarif-trivy', [])
        assert len(trivy_results) == 2, f"Expected 2 Trivy results, got {len(trivy_results)}"

        trivy_cve_ids = [r.get('id') for r in trivy_results]
        expected_trivy_ids = ['CVE-2024-0001', 'CVE-2024-0002']
        assert set(trivy_cve_ids) == set(expected_trivy_ids), f"Trivy CVE IDs mismatch"

        # Verify Checkov findings (SARIF parser uses 'sarif-checkov' as tool name)
        checkov_results = by_tool.get('sarif-checkov', [])
        assert len(checkov_results) == 1, f"Expected 1 Checkov result, got {len(checkov_results)}"
        assert checkov_results[0].get('id') == 'CKV_AWS_20'

        # Verify OSV Scanner findings
        osv_results = by_tool.get('osv-scanner', [])
        assert len(osv_results) == 1, f"Expected 1 OSV result, got {len(osv_results)}"
        assert osv_results[0].get('id') == 'GHSA-j8r2-6x86-q33q'

        # Verify ZAP findings
        zap_results = by_tool.get('zap', [])
        assert len(zap_results) == 1, f"Expected 1 ZAP result, got {len(zap_results)}"
        assert zap_results[0].get('id') == '10035'

    def test_ai_analysis_batch_processing(self):
        """Test that AI analysis processes 8 vulnerabilities correctly (when running analysis phase)"""
        # This test should run up to the analysis phase and verify AI analysis results
        result = self.run_process_artifacts(["--stop-after", "analysis"])
        assert result.returncode == 0, f"Script failed with return code {result.returncode}"

        # Should have analysis-specific output files
        analysis_files = list(self.temp_output_dir.glob("analyzed_vulnerabilities_*.json"))
        assert len(analysis_files) >= 1, "No analyzed vulnerabilities file created"

        with open(analysis_files[0], 'r') as f:
            results = json.load(f)

        # Should have 8 analyzed vulnerability results
        assert len(results) == 8, f"Expected 8 analysis results, got {len(results)}"

        # Each result should have AI analysis fields
        for result in results:
            assert 'vulnerability' in result, "Each result should have 'vulnerability' field"
            assert 'analysis' in result, "Each result should have 'analysis' field from AI processing"
            assert 'status' in result, "Each result should have 'status' field"

            # Check vulnerability fields
            vulnerability = result['vulnerability']
            assert 'tool' in vulnerability, "Vulnerability should have 'tool' field"
            assert 'id' in vulnerability, "Vulnerability should have 'id' field"

            # Check analysis fields
            analysis = result['analysis']
            assert 'raw_analysis' in analysis, "Analysis should have 'raw_analysis' field from AI processing"
            assert 'structured_analysis' in analysis, "Analysis should have 'structured_analysis' field from AI processing"

    def test_output_files_created_and_valid(self):
        """Test that all expected output files are created and contain valid data"""
        result = self.run_process_artifacts()
        assert result.returncode == 0, f"Script failed with return code {result.returncode}"

        # Expected output files for parsing phase only (using timestamp patterns)
        expected_file_patterns = [
            "parsing_summary_*.json",
            "parsed_vulnerabilities_*.json"
        ]

        created_files = {}
        for pattern in expected_file_patterns:
            files = list(self.temp_output_dir.glob(pattern))
            assert len(files) >= 1, f"No files found matching pattern: {pattern}"
            created_files[pattern] = files[0]  # Use the first match

        # Verify each file is non-empty and contains valid JSON/JSONL
        for pattern, file_path in created_files.items():
            assert file_path.stat().st_size > 0, f"File {file_path.name} is empty"

            if pattern.endswith("*.json"):
                # Validate JSON files
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    assert data is not None, f"File {file_path.name} contains invalid JSON"
            elif pattern.endswith("*.jsonl"):
                # Validate JSONL files
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    assert len(lines) > 0, f"JSONL file {file_path.name} has no lines"
                    # Validate first line is valid JSON
                    json.loads(lines[0])

    def test_dataset_content_accuracy(self):
        """Test that dataset files contain the correct number of entries"""
        result = self.run_process_artifacts(["--stop-after", "datasets"])
        assert result.returncode == 0, f"Script failed with return code {result.returncode}"

        # Should have dataset files created by the datasets phase
        train_files = list(self.temp_output_dir.glob("train_*.jsonl"))
        validation_files = list(self.temp_output_dir.glob("validation_*.jsonl"))
        narrativized_files = list(self.temp_output_dir.glob("narrativized_dataset_*.json"))

        # These SHOULD exist after datasets phase
        assert len(train_files) >= 1, f"No train files found after datasets phase"
        assert len(validation_files) >= 1, f"No validation files found after datasets phase"
        assert len(narrativized_files) >= 1, f"No narrativized dataset files found after datasets phase"

        # Verify train dataset content
        with open(train_files[0], 'r') as f:
            train_lines = f.readlines()

        # Should have training examples (exact count depends on split ratio)
        assert len(train_lines) > 0, f"Train dataset is empty"

        # Verify validation dataset content
        with open(validation_files[0], 'r') as f:
            validation_lines = f.readlines()

        assert len(validation_lines) > 0, f"Validation dataset is empty"

        # Verify narrativized dataset content
        with open(narrativized_files[0], 'r') as f:
            narrativized_data = json.load(f)

        # Should contain processed vulnerability data
        assert len(narrativized_data) == 8, f"Expected 8 narrativized vulnerabilities, got {len(narrativized_data)}"

    def test_summary_file_accuracy(self):
        """Test that summary file contains accurate vulnerability analysis counts"""
        result = self.run_process_artifacts()
        assert result.returncode == 0, f"Script failed with return code {result.returncode}"

        summary_files = list(self.temp_output_dir.glob("parsing_summary_*.json"))
        assert len(summary_files) >= 1, "No parsing summary file created"

        with open(summary_files[0], 'r') as f:
            summary = json.load(f)

        # Required fields in summary
        required_fields = ["total_analyzed", "by_tool", "analysis_timestamp"]
        for field in required_fields:
            assert field in summary, f"Summary missing required field: {field}"

        # Exact counts
        assert summary["total_analyzed"] == 8

        expected_tool_counts = {
            "semgrep": 3,
            "sarif-trivy": 2,  # SARIF parser prefixes tool names with 'sarif-'
            "sarif-checkov": 1,  # SARIF parser prefixes tool names with 'sarif-'
            "osv-scanner": 1,
            "zap": 1
        }

        for tool, expected_count in expected_tool_counts.items():
            actual_count = summary["by_tool"].get(tool, 0)
            assert actual_count == expected_count, f"Summary tool count mismatch for {tool}: expected {expected_count}, got {actual_count}"

    def test_error_handling_with_empty_directory(self):
        """Test script behavior when artifacts directory is empty"""
        # Create empty temp directory for artifacts
        empty_artifacts_dir = Path(tempfile.mkdtemp())

        try:
            # For this test, we need to capture output to check the error message
            result = subprocess.run(
                ["python3", str(self.script_path), "--artifacts-dir", str(empty_artifacts_dir), "--output-dir", str(self.temp_output_dir), "--stop-after", "parsing"],
                capture_output=True,
                text=True,
                cwd=self.script_path.parent
            )

            # Script should handle empty directory gracefully
            # It may return non-zero, but shouldn't crash
            stdout_text = result.stdout or ""
            stderr_text = result.stderr or ""
            assert "No security files found" in stdout_text or "No security files found" in stderr_text or result.returncode == 0

        finally:
            if empty_artifacts_dir.exists():
                shutil.rmtree(empty_artifacts_dir)

    def test_script_help_and_arguments(self):
        """Test that script accepts help argument and shows proper usage"""
        result = subprocess.run(
            ["python3", str(self.script_path), "--help"],
            capture_output=True,  # Keep capture for help test since we need to check output
            text=True,
            cwd=self.script_path.parent
        )

        assert result.returncode == 0, "Help command should succeed"
        assert "Process security artifacts" in result.stdout, "Help should contain description"
        assert "--artifacts-dir" in result.stdout, "Help should show artifacts-dir argument"
        assert "--stop-after" in result.stdout, "Help should show stop-after argument"
        assert "parsing,core-analysis,rag-enhancement,analysis,narrativization,datasets,training,upload" in result.stdout, "Help should show phase choices including new sub-phases"

    def test_script_with_different_output_directory(self):
        """Test script can write to custom output directory"""
        custom_output_dir = Path(tempfile.mkdtemp())

        try:
            result = self.run_process_artifacts([
                "--output-dir", str(custom_output_dir)
            ])

            assert result.returncode == 0, f"Script failed with custom output dir"

            # Check files were created in custom directory
            summary_files = list(custom_output_dir.glob("parsing_summary_*.json"))
            assert len(summary_files) >= 1, "No parsing summary file in custom output directory"

        finally:
            if custom_output_dir.exists():
                shutil.rmtree(custom_output_dir)

    @pytest.mark.slow
    def test_fine_tuning_artifacts_creation(self):
        """Test fine-tuning artifacts creation (slow test - only run when specifically testing fine-tuning)"""
        # This test would run without --skip-fine-tuning to test the full pipeline
        # Marked as slow since it involves actual model training
        pytest.skip("Slow test - only run when specifically testing fine-tuning pipeline")

    @pytest.mark.slow
    def test_model_upload_artifacts(self):
        """Test model upload artifacts creation (slow test - only run when specifically testing upload)"""
        # This test would run without --skip-model-upload to test upload pipeline
        # Marked as slow since it involves model conversion and upload
        pytest.skip("Slow test - only run when specifically testing model upload pipeline")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])