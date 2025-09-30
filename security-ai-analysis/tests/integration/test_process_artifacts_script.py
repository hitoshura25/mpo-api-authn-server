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

    def _cleanup_non_prerequisite_files(self, prerequisites: dict):
        """Remove all files from temp_output_dir except prerequisite files"""
        prerequisite_files = list(prerequisites.values())
        for file in self.temp_output_dir.glob("*"):
            if file not in prerequisite_files and file.is_file():
                file.unlink()

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
            print(f"🧪 Test Environment:")
            test_vars = ['OLMO_WORKSPACE_DIR', 'OLMO_KNOWLEDGE_BASE_DIR', 'OLMO_MAX_EPOCHS', 'OLMO_SAVE_STEPS', 'OLMO_MAX_STAGE1_ITERS', 'OLMO_MAX_STAGE2_ITERS']
            for var in test_vars:
                value = os.environ.get(var, 'Not set')
                print(f"     {var}: {value}")
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

            # Stream output in real-time with timeout protection
            import select
            import time

            timeout = 600  # 10 minutes timeout for long-running ML processes
            start_time = time.time()

            try:
                while True:
                    # Check if process has finished
                    if process.poll() is not None:
                        # Read any remaining output
                        remaining_output = process.stdout.read()
                        if remaining_output:
                            print(remaining_output.strip())
                        break

                    # Check for timeout
                    if time.time() - start_time > timeout:
                        print(f"⚠️ Process timeout after {timeout} seconds")
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        return -1

                    # Try to read output with select (Unix) or polling (cross-platform)
                    try:
                        if hasattr(select, 'select'):  # Unix systems
                            ready, _, _ = select.select([process.stdout], [], [], 1.0)
                            if ready:
                                output = process.stdout.readline()
                                if output:
                                    print(output.strip())
                                    sys.stdout.flush()
                        else:  # Windows fallback - use shorter readline timeout
                            output = process.stdout.readline()
                            if output:
                                print(output.strip())
                                sys.stdout.flush()
                            else:
                                time.sleep(0.1)  # Small delay to prevent CPU spinning
                    except Exception as e:
                        print(f"⚠️ Error reading process output: {e}")
                        break

                # Get final return code
                return_code = process.poll()
            except KeyboardInterrupt:
                print("🛑 Process interrupted by user")
                process.terminate()
                return -1
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
        self._cleanup_non_prerequisite_files(prerequisites)

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
        self._cleanup_non_prerequisite_files(prerequisites)

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

    # Removed test_error_handling_with_empty_directory - artifact downloading is out of scope for integration tests
    # Integration tests focus on phase logic using existing fixtures, not infrastructure concerns

    def test_script_help_and_arguments(self):
        """Test that script accepts help argument and core functionality works"""
        # Test 1: Help command should succeed
        result = subprocess.run(
            ["python3", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            cwd=self.script_path.parent
        )
        assert result.returncode == 0, "Help command should succeed"

        # Test 2: Verify core arguments work behaviorally instead of checking help text
        # Test that --only-parsing works (behavioral test)
        parsing_result = self.run_process_artifacts(["--only-parsing"])
        assert parsing_result.returncode == 0, "Only-parsing argument should work"

        # Test that --artifacts-dir works with custom directory
        custom_result = self.run_process_artifacts([
            "--only-parsing",
            "--artifacts-dir", str(self.test_artifacts_dir)
        ])
        assert custom_result.returncode == 0, "Artifacts-dir argument should work"

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
        self._cleanup_non_prerequisite_files(prerequisites)

        # Run only analysis summary phase
        result = self.run_process_artifacts([
            "--only-analysis-summary",
            "--rag-enhanced-input", str(prerequisites["rag_enhanced_file"])
        ])
        assert result.returncode == 0, f"Analysis phase failed with return code {result.returncode}"

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
        self._cleanup_non_prerequisite_files(prerequisites)

        # Run only narrativization phase
        result = self.run_process_artifacts([
            "--only-narrativization",
            "--analyzed-input", str(prerequisites["analyzed_file"])
        ])
        assert result.returncode == 0, f"Narrativization phase failed with return code {result.returncode}"

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
        self._cleanup_non_prerequisite_files(prerequisites)

        # Run only datasets phase
        result = self.run_process_artifacts([
            "--only-datasets",
            "--narrativized-input", str(prerequisites["narrativized_file"]),
            "--parsed-input", str(prerequisites["parsed_file"])
        ])
        assert result.returncode == 0, f"Datasets phase failed with return code {result.returncode}"

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
        assert result.returncode == 0, f"Core analysis phase failed with return code {result.returncode}"

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
        assert result.returncode == 0, f"RAG enhancement phase failed with return code {result.returncode}"

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

    def test_upload_phase_with_isolated_directory(self, completed_training_run):
        """Test upload phase with isolated test directory using structured training runs"""
        # Use the completed training run fixture which creates proper structured training run
        training_run = completed_training_run

        # Create mock dataset files for the upload phase requirement
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        dataset_files = f"{fixtures_dir / 'train_dataset_fixture.jsonl'},{fixtures_dir / 'validation_dataset_fixture.jsonl'}"

        # Test 1: Run without skip to test structured discovery (uploads blocked by test environment detection)
        # Note: No --model-dir needed since upload phase uses structured discovery
        result = self.run_process_artifacts([
            "--only-upload",
            "--dataset-files", dataset_files  # Required for upload phase
            # Note: NO --skip-model-upload to test path resolution with structured discovery
        ], realtime_output=True)

        # Fix the assertion - result is an integer, not an object with .returncode
        assert result == 0, f"Upload phase failed with return code {result}"

        # Verify the structured training run was properly created
        assert training_run.run_dir.exists(), "Training run directory should exist"
        assert training_run.manifest_path.exists(), "Manifest file should exist"

        # Verify stage 2 final model exists (what upload phase should discover)
        stage2_final_model_path = training_run.stage2_final_model_path
        assert stage2_final_model_path.exists(), "Stage 2 final model should exist"
        assert (stage2_final_model_path / "model.safetensors").exists(), "Model file should exist"
        assert (stage2_final_model_path / "config.json").exists(), "Config file should exist"

        # Verify upload processing occurred (behavioral check)
        # Since we created a fused model (complete model files), no PEFT conversion should occur
        # The upload should process the model directly without conversion
        # This is indicated by "Processing fused model - using original format" in logs

        # Test 2: Test skip behavior separately
        result_skip = self.run_process_artifacts([
            "--only-upload",
            "--dataset-files", dataset_files,
            "--skip-model-upload"  # Test skip behavior
        ], realtime_output=True)

        assert result_skip == 0, f"Skip upload failed with return code {result_skip}"

        # Verify skip behavior (behavioral check) - no PEFT conversion directories should exist
        # since we're using complete fused models, not LoRA adapters requiring conversion
        peft_dirs_after_skip = list(training_run.run_dir.glob("**/*_peft_converted"))
        assert len(peft_dirs_after_skip) == 0, "Skip upload with fused model should not create PEFT conversions"

        print(f"✅ Upload phase correctly discovered structured training run: {training_run.run_id}")

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

    def test_upload_invalid_model_structure_should_fail(self, tmp_path, monkeypatch):
        """Test that invalid model structure should fail fast with clear error"""
        # Create isolated test model directory with invalid structure
        isolated_models_dir = tmp_path / "test_models"
        model_timestamp = "20250926_120000"
        test_model_dir = isolated_models_dir / f"webauthn-security-sequential_{model_timestamp}"
        test_model_dir.mkdir(parents=True)

        # Create invalid structure (neither LoRA adapters nor fused model)
        (test_model_dir / "random_file.txt").write_text("not a model file")
        (test_model_dir / "irrelevant.json").write_text('{"not": "a model config"}')

        # Override config to use isolated test models directory for this test only
        monkeypatch.setenv("OLMO_FINE_TUNED_MODELS_DIR", str(isolated_models_dir))

        # Create mock dataset files for the upload phase requirement
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"
        dataset_files = f"{fixtures_dir / 'train_dataset_fixture.jsonl'},{fixtures_dir / 'validation_dataset_fixture.jsonl'}"

        # Run upload phase - this should fail fast with invalid model structure
        # Now uses config-driven discovery instead of --model-dir
        result = self.run_process_artifacts([
            "--only-upload",
            "--dataset-files", dataset_files
        ])

        # Verify upload fails for invalid model structure (behavioral check)
        assert result.returncode != 0, f"Upload should fail fast with invalid model structure, but succeeded"

        # Verify no PEFT conversion occurred for invalid structure (behavioral check)
        peft_dirs = list(isolated_models_dir.glob("**/*_peft_converted"))
        assert len(peft_dirs) == 0, "No PEFT conversion should occur for invalid model structure"

        # Verify proper fail-fast behavior - script should exit with error code
        # No need to check specific error message content, just that it failed appropriately

        print(f"✅ Invalid model structure correctly failed fast as expected")

    def test_training_phase_creates_complete_model_files(self, tmp_path, monkeypatch):
        """Test that training phase creates complete LoRA model structure with actual weights"""
        # Create isolated test directory for training output
        isolated_models_dir = tmp_path / "test_training_models"
        isolated_models_dir.mkdir(parents=True)

        # Override config to use isolated test models directory for this test only
        monkeypatch.setenv("OLMO_FINE_TUNED_MODELS_DIR", str(isolated_models_dir))

        # Create minimal input files required for training phase
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"

        # Run training phase only with config-driven output location (using medium-sized fixtures for faster execution)
        return_code = self.run_process_artifacts([
                "--only-training",
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

        # Find the created model directory in structured training-runs layout
        training_runs_dir = isolated_models_dir / "training-runs"
        assert training_runs_dir.exists(), f"Training runs directory not created: {training_runs_dir}"

        model_dirs = list(training_runs_dir.glob("webauthn-security-*"))
        assert len(model_dirs) > 0, f"No structured training runs created in {training_runs_dir}. " \
            f"This indicates the structured training runs are not being created!"

        # Use the newest training run (structured layout)
        model_dir = sorted(model_dirs)[-1]
        print(f"🎯 Using structured training run: {model_dir}")

        print(f"🔍 Checking structured model completeness in: {model_dir}")

        # Validate Stage 1 adapters (vulnerability analysis specialist)
        stage1_adapters = model_dir / "stage1" / "adapters"
        assert stage1_adapters.exists(), f"Stage 1 adapters directory missing: {stage1_adapters}"

        stage1_config = stage1_adapters / "adapter_config.json"
        stage1_weights = stage1_adapters / "adapters.safetensors"

        assert stage1_config.exists(), f"Missing Stage 1 adapter config: {stage1_config}"
        assert stage1_config.stat().st_size > 0, "Stage 1 adapter config file is empty"
        assert stage1_weights.exists(), f"Missing Stage 1 adapter weights: {stage1_weights}"
        assert stage1_weights.stat().st_size > 1000, f"Stage 1 weights file too small: {stage1_weights.stat().st_size} bytes"

        # Validate Stage 2 adapters (code fix generation specialist)
        stage2_adapters = model_dir / "stage2" / "adapters"
        assert stage2_adapters.exists(), f"Stage 2 adapters directory missing: {stage2_adapters}"

        stage2_config = stage2_adapters / "adapter_config.json"
        stage2_weights = stage2_adapters / "adapters.safetensors"

        assert stage2_config.exists(), f"Missing Stage 2 adapter config: {stage2_config}"
        assert stage2_config.stat().st_size > 0, "Stage 2 adapter config file is empty"
        assert stage2_weights.exists(), f"Missing Stage 2 adapter weights: {stage2_weights}"
        assert stage2_weights.stat().st_size > 1000, f"Stage 2 weights file too small: {stage2_weights.stat().st_size} bytes"

        # Validate Stage 2 final model (complete fused model)
        stage2_final = model_dir / "stage2" / "final-model"
        assert stage2_final.exists(), f"Stage 2 final model directory missing: {stage2_final}"

        final_config = stage2_final / "config.json"
        final_weights = stage2_final / "model.safetensors"

        assert final_config.exists(), f"Missing Stage 2 final model config: {final_config}"
        assert final_config.stat().st_size > 0, "Stage 2 final model config file is empty"
        assert final_weights.exists(), f"Missing Stage 2 final model weights: {final_weights}"
        assert final_weights.stat().st_size > 1000, f"Stage 2 final model weights file too small: {final_weights.stat().st_size} bytes"

        # Verify config is valid JSON (check Stage 1 as representative)
        with open(stage1_config, 'r') as f:
            import json
            config = json.load(f)
            # MLX adapter configs should have basic structure
            required_fields = ['model', 'data']  # Basic MLX LoRA config fields
            assert any(field in config for field in required_fields), f"Stage 1 adapter config missing required fields, got: {list(config.keys())}"

        print(f"✅ Sequential training completed successfully:")
        print(f"   Stage 1 adapters: {stage1_weights.stat().st_size} bytes")
        print(f"   Stage 2 adapters: {stage2_weights.stat().st_size} bytes")
        print(f"   Stage 2 final model: {final_weights.stat().st_size} bytes")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
