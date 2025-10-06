import json
import shutil
import subprocess
import os
import sys
from pathlib import Path

class TestProcessArtifactsScript:
    """Integration tests for the complete process_artifacts.py pipeline"""
    @classmethod
    def setup_class(cls):
        """Set up test environment"""
        test_root = Path(__file__).parent.parent
        fixtures_root = test_root / "fixtures"  
        cls.script_path = test_root.parent / "process_artifacts.py"
        cls.test_artifacts_dir = fixtures_root / "sample_security_artifacts"
        cls.phase_inputs_dir = fixtures_root / "phase_inputs"

        # Verify script and artifacts directory exist
        assert cls.script_path.exists(), f"Script not found: {cls.script_path}"
        assert cls.test_artifacts_dir.exists(), f"Test artifacts directory not found: {cls.test_artifacts_dir}"
        assert cls.phase_inputs_dir.exists(), f"Phase inputs directory not found: {cls.phase_inputs_dir}"

        cls.temp_output_dir = test_root / "phase_outputs"

        # Remove temporary output directory before tests
        if cls.temp_output_dir.exists():
            shutil.rmtree(cls.temp_output_dir)
        
    def setup_method(self):
        """Set up for each test"""

    def teardown_method(self):
        """Clean up after each test"""

    def _build_command_args(self, additional_args=None):
        """
        Helper method to build command arguments for process_artifacts.py
        Returns list of command arguments
        """
        # Minimal base arguments - let tests specify what they need
        base_args = [
            "python", str(self.script_path)
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
            print(f"🚀 Executing command: {' '.join(base_args)}")
            print(f"🔧 Working directory: {self.script_path.parent}")
            print(f"🧪 Test Environment:")
            test_vars = [
                'OLMO_WORKSPACE_DIR', 
                'OLMO_KNOWLEDGE_BASE_DIR', 
                'OLMO_MAX_EPOCHS', 
                'OLMO_SAVE_STEPS', 
                'OLMO_MAX_STAGE1_ITERS', 
                'OLMO_MAX_STAGE2_ITERS'
            ]
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

    def test_script_help_and_arguments(self):
        """Test that script accepts help argument and core functionality works"""
        # Test 1: Help command should succeed
        result = subprocess.run(
            ["python", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            cwd=self.script_path.parent
        )

        assert result.returncode == 0, "Help command should succeed"

    def test_parsing_only(self):
        """Test parsing only mode with sample artifacts"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-parsing"
            ],
            realtime_output=True
        )
        assert result == 0, f"Parsing only mode failed with exit code {result}"

        # Verify expected output file exists
        expected_output_file = self.temp_output_dir / "parsed_vulnerabilities.json"
        assert expected_output_file.exists(), f"Expected output file not found: {expected_output_file}"

        # Verify content of the output file
        import json
        with open(expected_output_file, 'r') as f:
            data = json.load(f)
            assert isinstance(data, list), "Output data should be a list"
            assert len(data) > 0, "Output data should not be empty"
            for vuln in data:
                assert 'id' in vuln, "Each vulnerability should have an 'id'"
                assert 'tool' in vuln, "Each vulnerability should have a 'tool'"
                assert 'severity' in vuln, "Each vulnerability should have a 'severity'"

    def test_categorization_only_fails_with_no_parsed_input(self):
        """Test categorization only mode with sample artifacts"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-categorization"
            ],
            realtime_output=True
        )
        assert result == 1, f"Categorization only mode should faile with no parsed input, got exit code {result}"

    def test_categorization_only_with_parsed_input(self): 
        """Test categorization only mode with sample artifacts and provided parsed input"""
        categorization_result = self.run_process_artifacts(
            additional_args=[
                "--only-categorization",
                "--parsed-input", str(self.phase_inputs_dir / "parsed_vulnerabilities.json")
            ],
            realtime_output=True
        )
        assert categorization_result == 0, f"Categorization only mode failed with exit code {categorization_result}"

        # Verify expected output file exists
        expected_analysis_file = self.temp_output_dir / "categorized_vulnerabilities.json"
        assert expected_analysis_file.exists(), f"Expected analysis file not found: {expected_analysis_file}"

        # Verify content of the analysis file
        import json
        with open(expected_analysis_file, 'r') as f:
            data = json.load(f)
            assert isinstance(data, list), "Analysis data should be a list"
            assert len(data) > 0, "Analysis data should not be empty"
            for item in data:
                assert 'id' in item, "Each analysis item should have an 'id'"
                assert 'tool' in item, "Each analysis item should have a 'tool'"
                assert 'security_category' in item, "Each analysis item should have a 'security_category'"
                assert 'category_confidence' in item, "Each analysis item should have a 'category_confidence'"

    def test_narrativization_only_fails_with_no_categorized_input(self):
        """Test narrativization only mode fails with no categorized input"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-narrativization"
            ],
            realtime_output=True
        )
        assert result == 1, f"Narrativization only mode should fail with no categorized input, got exit code {result}"

    def test_narrativization_only_with_categorized_input(self):
        """Test narrativization only mode with provided categorized input"""
        narrativization_result = self.run_process_artifacts(
            additional_args=[
                "--only-narrativization",
                "--categorized-input", str(self.phase_inputs_dir / "categorized_vulnerabilities.json")
            ],
            realtime_output=True
        )
        assert narrativization_result == 0, f"Narrativization only mode failed with exit code {narrativization_result}"

        # Verify expected output file exists
        expected_narrativization_file = self.temp_output_dir / "narrativized_analyses.json"
        assert expected_narrativization_file.exists(), f"Expected narrativization file not found: {expected_narrativization_file}"

        # Verify content of the narrativization file
        import json
        with open(expected_narrativization_file, 'r') as f:
            data = json.load(f)
            assert isinstance(data, list), "Narrativization data should be a list"
            assert len(data) > 0, "Narrativization data should not be empty"
            for item in data:
                assert 'ai_analysis' in item, "Each narrativized item should have an 'ai_analysis'"
                assert 'narrative' in item, "Each narrativized item should have a 'narrative'"
                assert 'vulnerability' in item, "Each narrativized item should have a 'vulnerability'"
                vulnerability = item['vulnerability']
                assert 'id' in vulnerability, "Each narrativized item should have an 'id'"
                assert 'tool' in vulnerability, "Each narrativized item should have a 'tool'"
                assert 'security_category' in vulnerability, "Each narrativized item should have a 'security_category'"
                assert 'category_confidence' in vulnerability, "Each narrativized item should have a 'category_confidence'"

    def test_datasets_only_fails_with_no_narrativized_input(self):
        """Test dataset construction only mode fails with no narrativized input"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-datasets"
            ],
            realtime_output=True
        )
        assert result == 1, f"Dataset construction only mode should fail with no narrativized input, got exit code {result}"

    def test_datasets_only_with_narrativized_input(self):
        """Test dataset construction only mode with provided narrativized input"""
        datasets_result = self.run_process_artifacts(
            additional_args=[
                "--only-datasets",
                "--narrativized-input", str(self.phase_inputs_dir / "narrativized_analyses.json")
            ],
            realtime_output=True
        )
        assert datasets_result == 0, f"Dataset construction only mode failed with exit code {datasets_result}"

        # Verify expected output files exist
        expected_train_file = self.temp_output_dir / "train_dataset.jsonl"
        expected_validation_file = self.temp_output_dir / "validation_dataset.jsonl"
        assert expected_train_file.exists(), f"Expected train dataset file not found: {expected_train_file}"
        assert expected_validation_file.exists(), f"Expected validation dataset file not found: {expected_validation_file}"

        # Verify content of the train dataset file
        with open(expected_train_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) > 0, "Train dataset file should not be empty"
            for line in lines:
                item = json.loads(line)
                assert 'messages' in item, "Each train dataset item should have 'messages'"
                assert 'metadata' in item, "Each train dataset item should have 'metadata'"
                for message in item['messages']:
                    assert 'role' in message, "Each message should have a 'role'"   
                    assert 'content' in message, "Each message should have 'content'"
                metadata = item['metadata']
                assert 'quality' in metadata, "Metadata should have 'quality'"
                assert 'source' in metadata, "Metadata should have 'source'"
                assert 'chat_template' in metadata, "Metadata should have 'chat_template'"

        # Verify content of the validation dataset file
        with open(expected_validation_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) > 0, "Validation dataset file should not be empty"
            for line in lines:
                item = json.loads(line)
                assert 'messages' in item, "Each validation dataset item should have 'messages'"
                assert 'metadata' in item, "Each validation dataset item should have 'metadata'"
                for message in item['messages']:
                    assert 'role' in message, "Each message should have a 'role'"   
                    assert 'content' in message, "Each message should have 'content'"
                metadata = item['metadata']
                assert 'quality' in metadata, "Metadata should have 'quality'"
                assert 'source' in metadata, "Metadata should have 'source'"
                assert 'chat_template' in metadata, "Metadata should have 'chat_template'"

    def test_training_only_fails_with_no_datasets(self):
        """Test training only mode fails with no datasets"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-training"
            ],
            realtime_output=True
        )
        assert result == 1, f"Training only mode should fail with no datasets, got exit code {result}"

    def test_training_only_fails_with_no_validation_dataset(self):
        """Test training only mode fails with no validation dataset"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-training",
                "--train-dataset", str(self.phase_inputs_dir / "train_dataset.jsonl")
            ],
            realtime_output=True
        )
        assert result == 1, f"Training only mode should fail with no validation dataset, got exit code {result}"

    def test_training_only_fails_with_no_train_dataset(self):
        """Test training only mode fails with no train dataset"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-training",
                "--validation-dataset", str(self.phase_inputs_dir / "validation_dataset.jsonl")
            ],
            realtime_output=True
        )
        assert result == 1, f"Training only mode should fail with no train dataset, got exit code {result}"

    def test_training_only_with_datasets(self, test_models_dir):
        """Test training only mode with provided datasets"""
        training_result = self.run_process_artifacts(
            additional_args=[
                "--only-training",
                "--train-dataset", str(self.phase_inputs_dir / "train_dataset.jsonl"),
                "--validation-dataset", str(self.phase_inputs_dir / "validation_dataset.jsonl")
            ],
            realtime_output=True
        )
        assert training_result == 0, f"Training only mode failed with exit code {training_result}"

        # Verify expected model output directory exists
        assert test_models_dir.exists(), f"Expected model output directory not found: {test_models_dir}"

        # Verify model files exist in the output directory
        model_dir = list(test_models_dir.glob("*"))
        assert len(model_dir) == 1, "No model directory found in the output directory"
        adapters_dir = model_dir[0] / "adapters"
        assert adapters_dir.exists(), f"Adapters directory not found in model output: {adapters_dir}"
        assert (adapters_dir / 'adapters.safetensors').exists(), f"Adapters file not found in: {adapters_dir}"