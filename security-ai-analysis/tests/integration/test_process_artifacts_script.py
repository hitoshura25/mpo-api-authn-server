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

    def create_prerequisite_files_up_to(self, target_phase):
        """Return paths to fixture files needed for testing target_phase"""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"

        if target_phase == "vulnerability-analysis":
            # Return direct path to parsed vulnerabilities fixture
            return {"parsed_file": fixtures_dir / "parsed_vulnerabilities_fixture.json"}

        elif target_phase == "rag-enhancement":
            # Return path to vulnerability analysis fixture for RAG enhancement
            return {
                "vulnerability_analysis_file": fixtures_dir / "vulnerability_analysis_fixture.json"
            }

        elif target_phase == "analysis-summary":
            # Return paths to analysis prerequisites
            return {
                "parsed_file": fixtures_dir / "parsed_vulnerabilities_fixture.json",
                "rag_enhanced_file": fixtures_dir / "rag_enhanced_fixture.json"
            }

        elif target_phase == "narrativization":
            # Return path to analyzed vulnerabilities fixture
            return {"analyzed_file": fixtures_dir / "analyzed_vulnerabilities_fixture.json"}

        elif target_phase == "datasets":
            # Return paths to both narrativized and parsed fixtures
            return {
                "narrativized_file": fixtures_dir / "narrativized_fixture.json",
                "parsed_file": fixtures_dir / "parsed_vulnerabilities_fixture.json"
            }

        elif target_phase == "training":
            # Return paths to training dataset fixtures
            return {
                "train_file": fixtures_dir / "train_dataset_fixture.jsonl",
                "validation_file": fixtures_dir / "validation_dataset_fixture.jsonl",
                "narrativized_file": fixtures_dir / "narrativized_fixture.json"
            }

        elif target_phase == "upload":
            # Return path to model artifacts fixture and dataset files
            return {
                "model_dir": fixtures_dir / "model_artifacts_fixture",
                "dataset_files": f"{fixtures_dir / 'train_dataset_fixture.jsonl'},{fixtures_dir / 'validation_dataset_fixture.jsonl'}"
            }

        else:
            raise ValueError(f"Unknown target phase: {target_phase}")

    def run_process_artifacts(self, additional_args=None):
        """
        Helper method to run process_artifacts.py with controlled test data
        Returns CompletedProcess result
        """
        # Minimal base arguments - let tests specify what they need
        base_args = [
            "python3", str(self.script_path)
        ]

        # Always provide default artifacts-dir and output-dir if not specified in additional_args
        if additional_args:
            # Check if artifacts-dir and output-dir are already provided
            has_artifacts_dir = any("--artifacts-dir" in str(arg) for arg in additional_args)
            has_output_dir = any("--output-dir" in str(arg) for arg in additional_args)

            if not has_artifacts_dir:
                base_args.extend(["--artifacts-dir", str(self.test_data_dir)])
            if not has_output_dir:
                base_args.extend(["--output-dir", str(self.temp_output_dir)])

            base_args.extend(additional_args)
        else:
            # No additional args, provide defaults and default to parsing only
            base_args.extend([
                "--artifacts-dir", str(self.test_data_dir),
                "--output-dir", str(self.temp_output_dir),
                "--only-parsing"
            ])

        # Run the script (capture output for testing)
        result = subprocess.run(
            base_args,
            text=True,
            capture_output=True,
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
        # Create prerequisite files and run analysis summary phase
        prerequisites = self.create_prerequisite_files_up_to("analysis-summary")

        # Clear output except for prerequisites
        prerequisite_files = list(prerequisites.values())
        for file in self.temp_output_dir.glob("*"):
            if file not in prerequisite_files and file.is_file():
                file.unlink()

        result = self.run_process_artifacts([
            "--only-analysis-summary",
            "--rag-enhanced-input", str(prerequisites["rag_enhanced_file"])
        ])
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
        # Create prerequisite files and run datasets phase
        prerequisites = self.create_prerequisite_files_up_to("datasets")

        # Clear output except for prerequisites
        prerequisite_files = list(prerequisites.values())
        for file in self.temp_output_dir.glob("*"):
            if file not in prerequisite_files and file.is_file():
                file.unlink()

        result = self.run_process_artifacts([
            "--only-datasets",
            "--narrativized-input", str(prerequisites["narrativized_file"]),
            "--parsed-input", str(prerequisites["parsed_file"])
        ])
        assert result.returncode == 0, f"Script failed with return code {result.returncode}"

        # Should have dataset files created by the datasets phase
        train_files = list(self.temp_output_dir.glob("train_*.jsonl"))
        validation_files = list(self.temp_output_dir.glob("validation_*.jsonl"))

        # These SHOULD exist after datasets phase
        assert len(train_files) >= 1, f"No train files found after datasets phase"
        assert len(validation_files) >= 1, f"No validation files found after datasets phase"

        # Verify train dataset content
        with open(train_files[0], 'r') as f:
            train_lines = f.readlines()

        # Should have training examples (exact count depends on split ratio)
        assert len(train_lines) > 0, f"Train dataset is empty"

        # Verify validation dataset content
        with open(validation_files[0], 'r') as f:
            validation_lines = f.readlines()

        assert len(validation_lines) > 0, f"Validation dataset is empty"

        # Verify dataset creation completed successfully - train/validation files are sufficient validation
        # The datasets phase processes narratives from fixture and creates JSONL training datasets

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
                ["python3", str(self.script_path), "--artifacts-dir", str(empty_artifacts_dir), "--output-dir", str(self.temp_output_dir), "--only-parsing"],
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
        assert "--only-parsing" in result.stdout, "Help should show only-parsing argument"
        assert "--only-vulnerability-analysis" in result.stdout, "Help should show only-vulnerability-analysis argument"
        assert "--parsed-input" in result.stdout, "Help should show parsed-input argument"
        assert "--narrativized-input" in result.stdout, "Help should show narrativized-input argument"

    def test_script_with_different_output_directory(self):
        """Test script can write to custom output directory"""
        custom_output_dir = Path(tempfile.mkdtemp())

        try:
            result = self.run_process_artifacts([
                "--only-parsing", "--output-dir", str(custom_output_dir)
            ])

            assert result.returncode == 0, f"Script failed with custom output dir"

            # Check files were created in custom directory
            summary_files = list(custom_output_dir.glob("parsing_summary_*.json"))
            assert len(summary_files) >= 1, "No parsing summary file in custom output directory"

        finally:
            if custom_output_dir.exists():
                shutil.rmtree(custom_output_dir)

    def test_parsing_phase_outputs(self):
        """Test all parsing phase outputs in single execution"""
        result = self.run_process_artifacts(["--only-parsing"])
        assert result.returncode == 0, f"Parsing phase failed: {result.stderr}"

        # Test 1: Parsed vulnerabilities file structure
        parsed_files = list(self.temp_output_dir.glob("parsed_vulnerabilities_*.json"))
        assert len(parsed_files) > 0, "Should have parsed vulnerabilities file"

        with open(parsed_files[0]) as f:
            parsed_data = json.load(f)

        assert len(parsed_data) > 0, "Parsed vulnerabilities should not be empty"

        # Test 2: Raw vulnerability data structure (needed by enhanced dataset creator)
        successful_results = [r for r in parsed_data if r.get('status') == 'success']
        assert len(successful_results) > 0, "Should have successful parsing results"

        sample_vuln = successful_results[0]['vulnerability']
        assert 'tool' in sample_vuln, f"Parsed vulnerability should have 'tool' field: {list(sample_vuln.keys())}"
        assert 'id' in sample_vuln, f"Parsed vulnerability should have 'id' field: {list(sample_vuln.keys())}"
        assert 'narrative' not in sample_vuln, f"Raw vulnerability should not have 'narrative': {list(sample_vuln.keys())}"

        # Test 3: URL-based vulnerabilities should be identifiable
        zap_vulns = [r['vulnerability'] for r in successful_results
                    if r['vulnerability'].get('tool') == 'zap']
        if zap_vulns:
            # ZAP vulnerabilities should have URL info that can be mapped later
            for zap_vuln in zap_vulns:
                assert 'site_host' in zap_vuln or 'url' in zap_vuln or 'path' in zap_vuln, \
                    f"ZAP vulnerability should have URL info for mapping: {list(zap_vuln.keys())}"

    def test_analysis_summary_phase_outputs(self):
        """Test analysis summary phase outputs in single execution"""
        # Create prerequisite files
        prerequisites = self.create_prerequisite_files_up_to("analysis-summary")

        # Clear output except for prerequisites
        prerequisite_files = list(prerequisites.values())
        for file in self.temp_output_dir.glob("*"):
            if file not in prerequisite_files and file.is_file():
                file.unlink()

        # Run only analysis summary phase
        result = self.run_process_artifacts([
            "--only-analysis-summary",
            "--rag-enhanced-input", str(prerequisites["rag_enhanced_file"])
        ])
        assert result.returncode == 0, f"Analysis phase failed: {result.stderr}"

        # Test 1: Analysis output files exist
        analysis_files = list(self.temp_output_dir.glob("analyzed_vulnerabilities_*.json"))
        assert len(analysis_files) > 0, "Analysis output file should exist"

        with open(analysis_files[0]) as f:
            analysis_results = json.load(f)

        # Test 2: Vulnerability data preserved through analysis
        # Use fixture file instead of temp output since we use fixture-based testing
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        parsed_fixture = fixtures_dir / "parsed_vulnerabilities_fixture.json"
        with open(parsed_fixture) as f:
            parsed_results = json.load(f)

        original_vuln_ids = {r['vulnerability']['id'] for r in parsed_results
                            if r.get('status') == 'success' and r.get('vulnerability', {}).get('id')}
        analysis_vuln_ids = {r['vulnerability']['id'] for r in analysis_results
                            if r.get('status') == 'success' and r.get('vulnerability', {}).get('id')}

        assert original_vuln_ids == analysis_vuln_ids, \
            f"Vulnerability IDs should be preserved: original={len(original_vuln_ids)}, analysis={len(analysis_vuln_ids)}"

        # Test 3: URL-to-Code mapping should enhance ZAP vulnerabilities
        zap_results = [r for r in analysis_results
                       if r.get('status') == 'success' and
                       r.get('vulnerability', {}).get('tool') == 'zap']

        if zap_results:
            for zap_result in zap_results:
                vuln_data = zap_result['vulnerability']
                # SHOULD FAIL: ZAP vulnerabilities should have file_path after URL mapping
                assert 'file_path' in vuln_data or 'mapped_file_path' in vuln_data, \
                    f"ZAP vulnerability should have file mapping: {list(vuln_data.keys())}"

                if 'file_path' in vuln_data or 'mapped_file_path' in vuln_data:
                    assert 'line_number' in vuln_data or 'mapped_line' in vuln_data, \
                        f"Mapped ZAP vulnerability should have line info: {list(vuln_data.keys())}"

    def test_narrativization_phase_outputs(self):
        """Test narrativization phase outputs in single execution"""
        # Create prerequisite files
        prerequisites = self.create_prerequisite_files_up_to("narrativization")

        # Clear output except for prerequisites
        prerequisite_files = list(prerequisites.values())
        for file in self.temp_output_dir.glob("*"):
            if file not in prerequisite_files and file.is_file():
                file.unlink()

        # Run only narrativization phase
        result = self.run_process_artifacts([
            "--only-narrativization",
            "--analyzed-input", str(prerequisites["analyzed_file"])
        ])
        assert result.returncode == 0, f"Narrativization phase failed: {result.stderr}"

        # Test 1: Narrativized output exists
        narrativized_files = list(self.temp_output_dir.glob("narrativized_*.json"))
        assert len(narrativized_files) > 0, "Narrativized file should exist"

        with open(narrativized_files[0]) as f:
            narrativized_data = json.load(f)

        assert len(narrativized_data) > 0, "Narrativized data should not be empty"

        # Test 2: Narrativized data structure
        sample = narrativized_data[0]
        assert 'narrative' in sample, f"Narrativized data should have narrative: {list(sample.keys())}"
        assert 'vulnerability_id' in sample, f"Narrativized data should have vulnerability_id: {list(sample.keys())}"

        # Test 3: Fixture files should be available for datasets phase (outside temp dir)
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        required_fixture_files = [
            ("parsed_vulnerabilities_fixture.json", "original vulnerability data"),
            ("analyzed_vulnerabilities_fixture.json", "analyzed vulnerability data"),
            ("narrativized_fixture.json", "narrativized content")
        ]

        for fixture_filename, description in required_fixture_files:
            fixture_path = fixtures_dir / fixture_filename
            assert fixture_path.exists(), f"Should have {description} fixture: {fixture_path}"

            with open(fixture_path) as f:
                data = json.load(f)
            assert len(data) > 0, f"{description} fixture should not be empty"

    def test_datasets_phase_outputs(self):
        """Test datasets phase outputs in single execution"""
        # Create prerequisite files
        prerequisites = self.create_prerequisite_files_up_to("datasets")

        # Clear output except for prerequisites
        prerequisite_files = list(prerequisites.values())
        for file in self.temp_output_dir.glob("*"):
            if file not in prerequisite_files and file.is_file():
                file.unlink()

        # Run only datasets phase
        result = self.run_process_artifacts([
            "--only-datasets",
            "--narrativized-input", str(prerequisites["narrativized_file"]),
            "--parsed-input", str(prerequisites["parsed_file"])
        ])
        assert result.returncode == 0, f"Datasets phase failed: {result.stderr}"

        # Test 1: Standard dataset files created
        train_files = list(self.temp_output_dir.glob("train_*.jsonl"))
        validation_files = list(self.temp_output_dir.glob("validation_*.jsonl"))

        assert len(train_files) > 0, "Training dataset file should be created"
        assert len(validation_files) > 0, "Validation dataset file should be created"

        # Test 2: Enhanced dataset creator should receive correct input
        # Check if enhanced dataset directory was created (indicates EnhancedDatasetCreator was called)
        enhanced_dirs = list(Path("enhanced_datasets/code-aware-training").glob("*"))

        if enhanced_dirs:
            # Test 3: Enhanced dataset files should exist
            enhanced_file = None
            for dir_path in enhanced_dirs:
                potential_file = dir_path / "enhanced_examples.jsonl"
                if potential_file.exists():
                    enhanced_file = potential_file
                    break

            # SHOULD FAIL: Enhanced examples file should exist if enhanced dataset creator ran successfully
            assert enhanced_file is not None, "Enhanced examples JSONL file should be created"

            # Test 4: Enhanced examples should have code context
            with open(enhanced_file) as f:
                enhanced_examples = [json.loads(line) for line in f]

            # SHOULD FAIL: Should have enhanced examples with code context
            assert len(enhanced_examples) > 0, "Should have enhanced examples"

            code_aware_examples = 0
            for example in enhanced_examples:
                metadata = example.get('metadata', {})
                if 'file_path' in metadata or 'code_context' in metadata:
                    code_aware_examples += 1

            assert code_aware_examples > 0, \
                f"Should have code-aware examples: {code_aware_examples}/{len(enhanced_examples)}"

        # Test 5: Verify datasets phase used correct input data
        # Use fixture file directly instead of temp output since we use fixture-based testing
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        parsed_fixture = fixtures_dir / "parsed_vulnerabilities_fixture.json"
        with open(parsed_fixture) as f:
            parsed_data = json.load(f)

        raw_vulns = [r['vulnerability'] for r in parsed_data if r.get('status') == 'success']

        # Check if any training examples reference the original vulnerability structure
        with open(train_files[0]) as f:
            train_examples = [json.loads(line) for line in f]

        # Enhanced examples should exist if raw vulnerabilities were properly passed
        enhanced_train_examples = [ex for ex in train_examples
                                  if ex.get('metadata', {}).get('enhancement_type') == 'code_aware']

        if len(raw_vulns) > 0 and len(enhanced_dirs) > 0:
            # SHOULD FAIL: If we have raw vulnerabilities and enhanced dataset creator ran,
            # we should have some enhanced examples
            assert len(enhanced_train_examples) > 0 or len(enhanced_examples) > 0, \
                f"Should have enhanced examples when raw vulnerabilities available: {len(raw_vulns)} raw vulns"

    def test_vulnerability_analysis_phase_outputs(self):
        """Test vulnerability analysis phase outputs in single execution"""
        # Use fixture-based approach for vulnerability analysis prerequisites
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        parsed_fixture = fixtures_dir / "parsed_vulnerabilities_fixture.json"

        # Run only vulnerability analysis with fixture input
        result = self.run_process_artifacts([
            "--only-vulnerability-analysis",
            "--parsed-input", str(parsed_fixture)
        ])
        assert result.returncode == 0, f"Core analysis phase failed: {result.stderr}"

        # Test 1: Core analysis output files exist
        core_analysis_files = list(self.temp_output_dir.glob("core_analysis_*.json"))
        assert len(core_analysis_files) > 0, "Core analysis output file should exist"

        with open(core_analysis_files[0]) as f:
            core_results = json.load(f)

        # Test 2: All vulnerabilities processed
        assert len(core_results) > 0, "Core analysis should process vulnerabilities"

        # Test 3: Core analysis structure validation
        successful_results = [r for r in core_results if r.get('status') == 'success']
        assert len(successful_results) > 0, "Should have successful core analysis results"

        sample_result = successful_results[0]
        assert 'vulnerability' in sample_result, "Core analysis should preserve vulnerability data"
        assert 'analysis' in sample_result, "Core analysis should contain analysis results"

        # Test 4: Analysis should have required fields
        analysis = sample_result['analysis']
        required_fields = ['vulnerability_id', 'severity', 'tool']
        for field in required_fields:
            assert field in analysis, f"Analysis should have {field}: {list(analysis.keys())}"

    def test_rag_enhancement_phase_outputs(self):
        """Test RAG enhancement phase outputs in single execution"""
        # Use fixture-based approach for RAG enhancement prerequisites
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        vuln_analysis_fixture = fixtures_dir / "vulnerability_analysis_fixture.json"

        # Run only RAG enhancement with fixture input
        result = self.run_process_artifacts([
            "--only-rag-enhancement",
            "--vulnerability-analysis-input", str(vuln_analysis_fixture)
        ])
        assert result.returncode == 0, f"RAG enhancement phase failed: {result.stderr}"

        # Test 1: RAG enhanced output files exist
        rag_files = list(self.temp_output_dir.glob("rag_enhanced_analysis_*.json"))
        assert len(rag_files) > 0, "RAG enhanced analysis file should exist"

        with open(rag_files[0]) as f:
            rag_results = json.load(f)

        # Test 2: Data preserved through RAG enhancement
        with open(vuln_analysis_fixture) as f:
            core_results = json.load(f)

        assert len(rag_results) == len(core_results), \
            f"RAG enhancement should preserve result count: core={len(core_results)}, rag={len(rag_results)}"

        # Test 3: RAG processing indicators
        # RAG enhancement may add metadata or enhance existing analysis
        successful_rag = [r for r in rag_results if r.get('status') == 'success']
        assert len(successful_rag) > 0, "Should have successful RAG enhanced results"

        # Test 4: Structure preserved from core analysis
        sample_rag = successful_rag[0]
        assert 'vulnerability' in sample_rag, "RAG enhanced should preserve vulnerability data"
        assert 'analysis' in sample_rag, "RAG enhanced should preserve analysis data"

    def test_training_phase_outputs(self):
        """Test training phase with fixture inputs"""
        # Use fixture-based approach for training prerequisites
        prerequisites = self.create_prerequisite_files_up_to("training")

        # Actually call --only-training with fixture inputs
        result = self.run_process_artifacts([
            "--only-training",
            "--train-input", str(prerequisites["train_file"]),
            "--validation-input", str(prerequisites["validation_file"]),
            "--narrativized-input", str(prerequisites["narrativized_file"]),
            "--skip-model-upload"  # Skip upload during training
        ])
        assert result.returncode == 0, f"Training phase failed: {result.stderr}"

        # Test 1: Training phase executed successfully
        # The training phase always runs (sequential fine-tuning is mandatory)

        # Test 2: Validate that training phase completed without errors
        # (Actual model training validation is resource-intensive and tested separately)
        print(f"✅ Training phase completed successfully with fixtures")

    def test_upload_phase_outputs(self):
        """Test upload phase with fixture inputs"""
        # Use fixture-based approach for upload prerequisites
        prerequisites = self.create_prerequisite_files_up_to("upload")

        # Actually call --only-upload with fixture inputs (skip actual upload for testing)
        result = self.run_process_artifacts([
            "--only-upload",
            "--model-dir", str(prerequisites["model_dir"]),
            "--dataset-files", prerequisites["dataset_files"],
            "--skip-model-upload"  # Skip actual upload for testing
        ])
        assert result.returncode == 0, f"Upload phase failed: {result.stderr}"

        # Test 1: Verify upload was actually skipped
        assert "🛑 Upload skipped (--skip-model-upload flag)" in result.stdout, \
            "Upload skip message should appear in output"

        # Test 2: Verify upload status is marked as skipped
        assert "'upload_status': 'skipped'" in result.stdout, \
            "Upload status should be marked as skipped in summary"

        # Test 3: Ensure no upload attempts were made
        assert "📤 Starting upload phase..." not in result.stdout, \
            "Should not start upload phase when skipped"

        print(f"✅ Upload phase correctly skipped with --skip-model-upload flag")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])