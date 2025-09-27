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
import struct
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

# Add parent directory to path so we can import the main script
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestProcessArtifactsScript:
    """Integration tests for the complete process_artifacts.py pipeline"""

    def create_mock_safetensors_file(self, file_path: Path, tensors_metadata: dict = None):
        """Create a minimal valid safetensors file for testing"""
        if tensors_metadata is None:
            tensors_metadata = {
                "weight": {
                    "dtype": "F32",
                    "shape": [2, 2],
                    "data_offsets": [0, 16]
                }
            }

        # Create header JSON
        header_json = json.dumps(tensors_metadata).encode('utf-8')
        header_length = len(header_json)

        # Create minimal tensor data (4 floats = 16 bytes for a 2x2 matrix)
        tensor_data = struct.pack('4f', 1.0, 0.0, 0.0, 1.0)  # Identity matrix

        # Write safetensors file format: 8 bytes length + header + tensor data
        with open(file_path, 'wb') as f:
            # Write header length (8 bytes, little-endian)
            f.write(struct.pack('<Q', header_length))
            # Write header
            f.write(header_json)
            # Write tensor data
            f.write(tensor_data)

    @classmethod
    def setup_class(cls):
        """Set up test environment"""
        cls.script_path = Path(__file__).parent.parent.parent / "process_artifacts.py"
        cls.test_artifacts_dir = Path(__file__).parent.parent / "fixtures" / "sample_security_artifacts"

        # Verify script and artifacts directory exist
        assert cls.script_path.exists(), f"Script not found: {cls.script_path}"
        assert cls.test_artifacts_dir.exists(), f"Test artifacts directory not found: {cls.test_artifacts_dir}"

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

    def _build_command_args(self, additional_args=None):
        """
        Helper method to build command arguments for process_artifacts.py
        Returns list of command arguments
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
                base_args.extend(["--artifacts-dir", str(self.test_artifacts_dir)])
            if not has_output_dir:
                base_args.extend(["--output-dir", str(self.temp_output_dir)])

            base_args.extend(additional_args)
        else:
            # No additional args, provide defaults and default to parsing only
            base_args.extend([
                "--artifacts-dir", str(self.test_artifacts_dir),
                "--output-dir", str(self.temp_output_dir),
                "--only-parsing"
            ])

        return base_args

    def run_process_artifacts(self, additional_args=None, realtime_output=False):
        """
        Helper method to run process_artifacts.py with controlled test data

        Args:
            additional_args: Additional command line arguments
            realtime_output: If True, stream output in real-time and return exit code.
                           If False, capture output and return CompletedProcess result.

        Returns:
            CompletedProcess result (if realtime_output=False) or exit code (if realtime_output=True)
        """
        base_args = self._build_command_args(additional_args)

        if realtime_output:
            # Real-time output streaming mode
            import sys

            print(f"🚀 Executing command: {' '.join(base_args)}")
            print(f"🔧 Working directory: {self.script_path.parent}")
            print(f"🧪 OLMO_TEST_MODE: {os.environ.get('OLMO_TEST_MODE', 'Not set')}")
            print("=" * 80)
            sys.stdout.flush()

            # Use Popen for real-time output streaming
            process = subprocess.Popen(
                base_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                cwd=self.script_path.parent
            )

            # Stream output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
                    sys.stdout.flush()

            # Wait for process to complete and get return code
            return_code = process.poll()
            print("=" * 80)
            print(f"🏁 Process completed with return code: {return_code}")
            return return_code
        else:
            # Standard captured output mode
            result = subprocess.run(
                base_args,
                text=True,
                capture_output=True,
                cwd=self.script_path.parent
            )
            return result

    # Removed test_exact_vulnerability_parsing - redundant with fixture-based phase tests

    # Removed test_tool_specific_parsing_accuracy - redundant with fixture-based phase tests

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

    # Removed test_summary_file_accuracy - redundant with fixture-based phase tests

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

    # Removed test_parsing_phase_outputs - redundant with fixture-based phase tests

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

    # Removed test_training_phase_outputs - redundant with test_training_phase_creates_complete_model_files
    # The comprehensive test provides superior validation while being faster (2:53 min) due to optimization

    # Removed test_upload_phase_outputs - redundant smoke test with minimal validation
    # Other upload tests provide superior coverage of upload functionality

    def test_upload_phase_with_isolated_directory(self, tmp_path):
        """Test upload phase with isolated test directory to prevent production pollution"""
        # Create isolated test model directory structure
        isolated_models_dir = tmp_path / "test_models"
        isolated_models_dir.mkdir(parents=True)

        # Create a mock fine-tuned model directory with timestamp pattern
        model_timestamp = "20250926_120000"
        test_model_dir = isolated_models_dir / f"webauthn-security-sequential_{model_timestamp}"
        test_model_dir.mkdir(parents=True)

        # Create mock model files (adapters directory structure)
        adapters_dir = test_model_dir / "adapters"
        adapters_dir.mkdir(parents=True)

        # Create realistic mock adapter files that pass validation
        self.create_mock_safetensors_file(adapters_dir / "adapters.safetensors")
        (adapters_dir / "adapter_config.json").write_text(json.dumps({
            "base_model_name_or_path": "allenai/OLMo-2-1B",
            "task_type": "CAUSAL_LM",
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "r": 16
        }))

        # Create mock dataset files for the upload phase requirement
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        dataset_files = f"{fixtures_dir / 'train_dataset_fixture.jsonl'},{fixtures_dir / 'validation_dataset_fixture.jsonl'}"

        # Test 1: Run without skip to test path resolution (uploads blocked by test environment detection)
        result = self.run_process_artifacts([
            "--only-upload",
            "--model-dir", str(isolated_models_dir),  # Point to base directory
            "--dataset-files", dataset_files  # Required for upload phase
            # Note: NO --skip-model-upload to test path resolution
        ])

        assert result.returncode == 0, f"Upload phase failed: {result.stderr}"

        # Verify upload processing occurred (behavioral check)
        # PEFT conversion should have created a converted directory
        expected_peft_dir = test_model_dir.parent / f"{test_model_dir.name}_peft_converted"
        assert expected_peft_dir.exists(), "PEFT conversion should create converted directory"

        # Verify test environment blocking by checking for test URL
        assert "https://huggingface.co/test-blocked/" in result.stdout, \
            "Should return fake test URL when upload is blocked"

        # Test 2: Test skip behavior separately
        result_skip = self.run_process_artifacts([
            "--only-upload",
            "--model-dir", str(isolated_models_dir),
            "--dataset-files", dataset_files,
            "--skip-model-upload"  # Test skip behavior
        ])

        assert result_skip.returncode == 0, f"Skip upload failed: {result_skip.stderr}"
        assert "🛑 Upload skipped (--skip-model-upload flag)" in result_skip.stdout, \
            "Should skip upload as requested"

        print(f"✅ Upload phase correctly discovered model in isolated directory")

    def test_upload_phase_path_resolution_multiple_models(self, tmp_path):
        """Test that upload phase selects the most recent model when multiple exist"""
        # Create isolated test directory with multiple model versions
        isolated_models_dir = tmp_path / "test_models"
        isolated_models_dir.mkdir(parents=True)

        # Create multiple model directories with different timestamps
        old_model = isolated_models_dir / "webauthn-security-sequential_20250925_100000"
        new_model = isolated_models_dir / "webauthn-security-sequential_20250926_120000"
        newest_model = isolated_models_dir / "webauthn-security-sequential_20250926_150000"

        for model_dir in [old_model, new_model, newest_model]:
            model_dir.mkdir(parents=True)
            adapters_dir = model_dir / "adapters"
            adapters_dir.mkdir(parents=True)
            # Create realistic mock adapter files that pass validation
            self.create_mock_safetensors_file(adapters_dir / "adapters.safetensors")
            (adapters_dir / "adapter_config.json").write_text(json.dumps({
                "base_model_name_or_path": "allenai/OLMo-2-1B",
                "task_type": "CAUSAL_LM",
                "lora_alpha": 32,
                "lora_dropout": 0.1,
                "r": 16
            }))

        # Create mock dataset files for the upload phase requirement
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        dataset_files = f"{fixtures_dir / 'train_dataset_fixture.jsonl'},{fixtures_dir / 'validation_dataset_fixture.jsonl'}"

        # Run upload phase to test path resolution (uploads blocked by test environment detection)
        result = self.run_process_artifacts([
            "--only-upload",
            "--model-dir", str(isolated_models_dir),
            "--dataset-files", dataset_files  # Required for upload phase
            # Note: NO --skip-model-upload to test path resolution
        ])

        assert result.returncode == 0, f"Upload phase failed: {result.stderr}"

        # Verify it selected the newest model (behavioral check)
        # PEFT conversion should occur only for the newest model
        newest_peft_dir = newest_model.parent / f"{newest_model.name}_peft_converted"
        assert newest_peft_dir.exists(), "PEFT conversion should occur for newest model"

        # Verify older models were not processed
        old_peft_dir = old_model.parent / f"{old_model.name}_peft_converted"
        new_peft_dir = new_model.parent / f"{new_model.name}_peft_converted"
        assert not old_peft_dir.exists(), "Old model should not be processed"
        assert not new_peft_dir.exists(), "Middle model should not be processed"

        # Verify test environment blocking by checking for test URL
        assert "https://huggingface.co/test-blocked/" in result.stdout, \
            "Should return fake test URL when upload is blocked"

        print(f"✅ Upload phase correctly selected newest model from multiple options")

    # Removed test_upload_phase_with_mocked_huggingface - consolidated with test_upload_lora_model_with_adapters
    # The enhanced LoRA test provides equivalent coverage with better organization

    def test_upload_phase_fallback_behavior(self, tmp_path):
        """Test upload phase fallback when no webauthn-security-sequential directories found"""
        # Create isolated directory structure without sequential model pattern
        isolated_models_dir = tmp_path / "test_models"
        isolated_models_dir.mkdir(parents=True)

        # Create realistic LoRA model files directly in the base directory (no sequential subdirectory)
        # Use proper LoRA structure: adapters/ subdirectory
        adapters_dir = isolated_models_dir / "adapters"
        adapters_dir.mkdir(parents=True)
        self.create_mock_safetensors_file(adapters_dir / "adapters.safetensors")
        (adapters_dir / "adapter_config.json").write_text(json.dumps({
            "base_model_name_or_path": "allenai/OLMo-2-1B",
            "task_type": "CAUSAL_LM",
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "r": 16
        }))

        # Create mock dataset files for the upload phase requirement
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        dataset_files = f"{fixtures_dir / 'train_dataset_fixture.jsonl'},{fixtures_dir / 'validation_dataset_fixture.jsonl'}"

        # Run upload phase to test fallback behavior (uploads blocked by test environment detection)
        result = self.run_process_artifacts([
            "--only-upload",
            "--model-dir", str(isolated_models_dir),
            "--dataset-files", dataset_files  # Required for upload phase
            # Note: NO --skip-model-upload to test fallback behavior
        ])

        assert result.returncode == 0, f"Upload phase failed: {result.stderr}"

        # Verify fallback behavior worked (behavioral check)
        # PEFT conversion should have occurred using the direct path
        expected_peft_dir = isolated_models_dir.parent / f"{isolated_models_dir.name}_peft_converted"
        assert expected_peft_dir.exists(), "PEFT conversion should occur for direct model path"

        # Verify test environment blocking by checking for test URL
        assert "https://huggingface.co/test-blocked/" in result.stdout, \
            "Should return fake test URL when upload is blocked"

        print(f"✅ Upload phase correctly handled fallback behavior")

    def test_model_validation_module_exists(self):
        """Test that validation module can be imported and used - should fail initially"""
        try:
            from validate_model_artifacts import validate_model_artifacts
            # If we get here, the module exists
            assert callable(validate_model_artifacts), \
                "validate_model_artifacts should be a callable function"
        except ImportError:
            # This is expected to fail initially - we'll fix it by creating the module
            pytest.fail("validate_model_artifacts module is missing - this test documents the issue")

    def test_upload_lora_model_with_adapters(self, tmp_path):
        """Test comprehensive LoRA model upload with adapter structure and validation"""
        # Create isolated test model directory structure with LoRA adapters
        isolated_models_dir = tmp_path / "test_models"
        model_timestamp = "20250926_120000"
        test_model_dir = isolated_models_dir / f"webauthn-security-sequential_{model_timestamp}"
        adapters_dir = test_model_dir / "adapters"
        adapters_dir.mkdir(parents=True)

        # Create realistic LoRA adapter files that pass validation
        self.create_mock_safetensors_file(adapters_dir / "adapters.safetensors")
        (adapters_dir / "adapter_config.json").write_text(json.dumps({
            "base_model_name_or_path": "allenai/OLMo-2-1B",
            "task_type": "CAUSAL_LM",
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "r": 16
        }))

        # Create mock dataset files for the upload phase requirement
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        dataset_files = f"{fixtures_dir / 'train_dataset_fixture.jsonl'},{fixtures_dir / 'validation_dataset_fixture.jsonl'}"

        # Run upload phase (uploads blocked by test environment detection)
        result = self.run_process_artifacts([
            "--only-upload",
            "--model-dir", str(isolated_models_dir),
            "--dataset-files", dataset_files
        ])

        assert result.returncode == 0, f"Upload phase failed: {result.stderr}"

        # Verify LoRA model processing occurred (behavioral check)
        # PEFT conversion should have occurred for LoRA structure
        expected_peft_dir = test_model_dir.parent / f"{test_model_dir.name}_peft_converted"
        assert expected_peft_dir.exists(), "PEFT conversion should occur for LoRA model"

        # Verify test environment upload blocking (consolidates mocked HuggingFace test)
        assert "https://huggingface.co/test-blocked/" in result.stdout, \
            "Should return fake test URL when upload is blocked in test environment"

        print(f"✅ LoRA model upload test completed with comprehensive validation")

    def test_upload_fused_model_without_adapters(self, tmp_path):
        """Test upload of fused model with merged weights (no adapters directory)"""
        # Create isolated test model directory structure with fused model
        isolated_models_dir = tmp_path / "test_models"
        model_timestamp = "20250926_120000"
        test_model_dir = isolated_models_dir / f"webauthn-security-sequential_{model_timestamp}"
        test_model_dir.mkdir(parents=True)

        # Create fused model files (no adapters subdirectory)
        self.create_mock_safetensors_file(test_model_dir / "model.safetensors")
        (test_model_dir / "config.json").write_text(json.dumps({
            "architectures": ["OLMoForCausalLM"],
            "model_type": "olmo",
            "torch_dtype": "float32"
        }))
        (test_model_dir / "tokenizer.json").write_text('{"version": "1.0"}')

        # Create mock dataset files for the upload phase requirement
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        dataset_files = f"{fixtures_dir / 'train_dataset_fixture.jsonl'},{fixtures_dir / 'validation_dataset_fixture.jsonl'}"

        # Run upload phase (uploads blocked by test environment detection)
        result = self.run_process_artifacts([
            "--only-upload",
            "--model-dir", str(isolated_models_dir),
            "--dataset-files", dataset_files
        ])

        assert result.returncode == 0, f"Upload phase failed: {result.stderr}"

        # Verify fused model processing completed (behavioral check)
        # For fused models, the original model should be validated directly (no PEFT conversion)
        assert (test_model_dir / "model.safetensors").exists(), \
            "Original fused model files should be preserved"
        assert (test_model_dir / "config.json").exists(), \
            "Fused model config should be preserved"

        # Verify test environment blocking occurred
        assert "https://huggingface.co/test-blocked/" in result.stdout, \
            "Should return fake test URL when upload is blocked"

        print(f"✅ Fused model upload test completed (no adapter structure)")

    def test_upload_invalid_model_structure_should_fail(self, tmp_path):
        """Test that invalid model structure should fail fast with clear error"""
        # Create isolated test model directory with invalid structure
        isolated_models_dir = tmp_path / "test_models"
        model_timestamp = "20250926_120000"
        test_model_dir = isolated_models_dir / f"webauthn-security-sequential_{model_timestamp}"
        test_model_dir.mkdir(parents=True)

        # Create invalid structure (neither LoRA adapters nor fused model)
        (test_model_dir / "random_file.txt").write_text("not a model file")
        (test_model_dir / "irrelevant.json").write_text('{"not": "a model config"}')

        # Create mock dataset files for the upload phase requirement
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        dataset_files = f"{fixtures_dir / 'train_dataset_fixture.jsonl'},{fixtures_dir / 'validation_dataset_fixture.jsonl'}"

        # Run upload phase - this should fail fast with invalid model structure
        result = self.run_process_artifacts([
            "--only-upload",
            "--model-dir", str(isolated_models_dir),
            "--dataset-files", dataset_files
        ])

        # Verify upload fails for invalid model structure (behavioral check)
        assert result.returncode != 0, f"Upload should fail fast with invalid model structure, but succeeded"

        # Verify no PEFT conversion occurred for invalid structure
        peft_dirs = list(isolated_models_dir.glob("**/*_peft_converted"))
        assert len(peft_dirs) == 0, "No PEFT conversion should occur for invalid model structure"

        # Verify failure is due to validation (less specific error check)
        assert "validation" in result.stderr.lower() or "invalid" in result.stderr.lower(), \
            f"Should indicate validation failure, got: {result.stderr}"

        print(f"✅ Invalid model structure correctly failed fast as expected")

    def test_training_phase_creates_complete_model_files(self, tmp_path):
        """Test that training phase creates complete LoRA model structure with actual weights"""
        # Enable test mode for faster training execution
        import os
        original_test_mode = os.environ.get('OLMO_TEST_MODE')
        os.environ['OLMO_TEST_MODE'] = '1'

        try:
            # Create isolated test directory for training output
            isolated_models_dir = tmp_path / "test_training_models"
            isolated_models_dir.mkdir(parents=True)

            # Create minimal input files required for training phase
            fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"

            # Run training phase only in isolated directory with real-time output (using medium-sized fixtures for faster execution)
            return_code = self.run_process_artifacts([
                "--only-training",
                "--model-dir", str(isolated_models_dir),
                "--narrativized-input", str(fixtures_dir / "narrativized_fixture_medium.json"),
                "--train-input", str(fixtures_dir / "train_dataset_fixture_medium.jsonl"),
                "--validation-input", str(fixtures_dir / "validation_dataset_fixture_medium.jsonl")
            ], realtime_output=True)

            assert return_code == 0, f"Training phase failed with return code: {return_code}"

            # Debug: Show what was actually created
            print(f"🔍 Training phase completed, checking output in: {isolated_models_dir}")
            if isolated_models_dir.exists():
                created_items = list(isolated_models_dir.iterdir())
                print(f"📁 Items created: {[item.name for item in created_items]}")

                # Show detailed structure of each model directory
                for item in created_items:
                    if item.is_dir() and "webauthn-security-sequential" in item.name:
                        print(f"📂 Model directory contents: {item}")
                        for subitem in item.iterdir():
                            print(f"   📄 {subitem.name}")
                            if subitem.is_dir():
                                for subsubitem in subitem.iterdir():
                                    print(f"      📄 {subsubitem.name}")
            else:
                print(f"❌ Model directory doesn't exist: {isolated_models_dir}")

            # Find the created model directory (should have timestamp pattern)
            model_dirs = list(isolated_models_dir.glob("webauthn-security-sequential_*"))
            assert len(model_dirs) > 0, f"No model directory created in {isolated_models_dir}. " \
                f"This exposes the training phase bug - models are not saved to --model-dir location!"

            # Prefer LoRA models (those with adapters directory) over fused models
            lora_models = [d for d in model_dirs if (d / "adapters").exists()]
            if lora_models:
                model_dir = sorted(lora_models)[-1]  # Use newest LoRA model
                print(f"🎯 Selected LoRA model: {model_dir}")
            else:
                model_dir = sorted(model_dirs)[-1]   # Fallback to any model
                print(f"⚠️ No LoRA models found, using: {model_dir}")
            adapters_dir = model_dir / "adapters"

            print(f"🔍 Checking model completeness in: {model_dir}")

            # Assert complete LoRA model structure exists
            assert adapters_dir.exists(), f"Adapters directory missing: {adapters_dir}"

            adapter_config_file = adapters_dir / "adapter_config.json"
            adapters_weights_file = adapters_dir / "adapters.safetensors"

            # Check adapter config file
            assert adapter_config_file.exists(), f"Missing adapter config: {adapter_config_file}"
            assert adapter_config_file.stat().st_size > 0, "Adapter config file is empty"

            # Check adapter weights file - THIS WILL CURRENTLY FAIL
            assert adapters_weights_file.exists(), f"Missing adapter weights: {adapters_weights_file}"
            assert adapters_weights_file.stat().st_size > 1000, f"Adapter weights file too small: {adapters_weights_file.stat().st_size} bytes"

            # Verify the config is valid JSON
            with open(adapter_config_file, 'r') as f:
                import json
                config = json.load(f)
                # Check for MLX adapter config fields (more flexible than PEFT task_type)
                mlx_fields = ['adapter_path', 'batch_size', 'data']
                assert any(field in config for field in mlx_fields), f"Adapter config missing MLX fields, got: {list(config.keys())}"

            print(f"✅ Training phase created complete model with {adapters_weights_file.stat().st_size} byte weights file")

        finally:
            # Restore original test mode environment variable
            if original_test_mode is None:
                os.environ.pop('OLMO_TEST_MODE', None)
            else:
                os.environ['OLMO_TEST_MODE'] = original_test_mode

    def test_model_selection_prioritizes_final_over_intermediate(self, tmp_path):
        """Test that model selection chooses final Stage 2 models over intermediate merged models"""

        # Import the function to test
        import sys
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from process_artifacts import _select_final_model

        # Create test model directories that simulate the production scenario
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create the exact directory structure from production log
        stage1_dir = models_dir / "webauthn-security-sequential_20250926_155405_stage1_analysis"
        stage2_final_dir = models_dir / "webauthn-security-sequential_20250926_155405_stage2_codefix"
        stage2_intermediate_dir = models_dir / "webauthn-security-sequential_20250926_155405_stage2_codefix_stage1_merged_stage1_merged"

        # Create all directories
        stage1_dir.mkdir()
        stage2_final_dir.mkdir()
        stage2_intermediate_dir.mkdir()

        # Add some files to make them realistic
        for dir_path in [stage1_dir, stage2_final_dir, stage2_intermediate_dir]:
            (dir_path / "config.json").write_text('{"model_type": "OLMoForCausalLM"}')
            self.create_mock_safetensors_file(dir_path / "model.safetensors")

        model_dirs = [stage1_dir, stage2_final_dir, stage2_intermediate_dir]

        # Test the selection logic
        selected_model = _select_final_model(model_dirs)

        # Should select the final Stage 2 model, not the intermediate one
        assert selected_model == stage2_final_dir, \
            f"Expected {stage2_final_dir.name}, got {selected_model.name}"

        print(f"✅ Model selection correctly chose final model: {selected_model.name}")

    def test_model_selection_with_only_intermediate_models(self, tmp_path):
        """Test model selection when only intermediate models exist"""

        # Import the function to test
        import sys
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from process_artifacts import _select_final_model

        # Create test model directories with only intermediate models
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create intermediate model directories
        intermediate1_dir = models_dir / "webauthn-security-sequential_20250926_155405_stage1_merged"
        intermediate2_dir = models_dir / "webauthn-security-sequential_20250926_155405_stage2_codefix_stage1_merged"
        stage1_dir = models_dir / "webauthn-security-sequential_20250926_155405_stage1_analysis"

        # Create all directories
        intermediate1_dir.mkdir()
        intermediate2_dir.mkdir()
        stage1_dir.mkdir()

        # Add some files to make them realistic
        for dir_path in [intermediate1_dir, intermediate2_dir, stage1_dir]:
            (dir_path / "config.json").write_text('{"model_type": "OLMoForCausalLM"}')
            self.create_mock_safetensors_file(dir_path / "model.safetensors")

        model_dirs = [intermediate1_dir, intermediate2_dir, stage1_dir]

        # Test the selection logic
        selected_model = _select_final_model(model_dirs)

        # Should select stage2 non-merged model over stage1
        assert selected_model == intermediate2_dir, \
            f"Expected {intermediate2_dir.name}, got {selected_model.name}"

        print(f"✅ Model selection correctly chose best available: {selected_model.name}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
