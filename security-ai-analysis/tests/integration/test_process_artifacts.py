import json
import re
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
                assert 'fix' in vuln, "Each vulnerability should have a 'fix'"
                fix = vuln['fix']
                assert 'confidence' in fix, "Each fix should have a 'confidence'"
                assert 'description' in fix, "Each fix should have a 'description'"

                assert vuln['tool'] in ['trivy', 'osv-scanner', 'checkov', 'semgrep', 'zap'], f"Unexpected tool: {vuln['tool']}"
                if vuln['tool'] in ['trivy', 'osv-scanner']:
                    assert 'fixed_version' in vuln, f"Each vulnerability from {vuln['tool']} should have 'fixed_version'"
                    assert 'installed_version' in vuln, f"Each vulnerability from {vuln['tool']} should have 'installed_version'"


    def test_datasets_only_fails_with_no_parsed_vulnerabilities_input(self):
        """Test dataset construction only mode fails with no parsed vulnerabilities input"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-datasets"
            ],
            realtime_output=True
        )
        assert result == 1, f"Dataset construction only mode should fail with no parsed vulnerabilities input, got exit code {result}"

    def test_datasets_only_with_parsed_vulnerabilities_input(self):
        """Test dataset construction only mode with provided parsed vulnerabilities input"""
        datasets_result = self.run_process_artifacts(
            additional_args=[
                "--only-datasets",
                "--parsed-vulnerabilities-input", str(self.phase_inputs_dir / "parsed_vulnerabilities.json")
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
        assert (adapters_dir / 'training_metadata.json').exists(), f"training_metadata.json file not found in: {adapters_dir}"

    def test_evaluation_only_fails_with_no_test_dataset(self):
        """Test evaluation only mode fails with no test dataset"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-evaluation",
            ],
            realtime_output=True
        )
        assert result == 1, f"Evaluation only mode should fail with no test dataset, got exit code {result}"

    def test_evaluation_only_fails_with_no_adapters(self):
        """Test evaluation only mode fails with no model directory"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-evaluation",
                "--test-dataset", str(self.phase_inputs_dir / "test_dataset.jsonl"),
            ],
            realtime_output=True
        )
        assert result == 1, f"Evaluation only mode should fail with no model directory, got exit code {result}" 

    def test_evaluation_only_with_adapters_and_test_dataset(self):
        """Test evaluation only mode with provided model directory and test dataset"""
        eval_result = self.run_process_artifacts(
            additional_args=[
                "--only-evaluation",
                "--adapter-input", str(self.phase_inputs_dir / "adapters"),
                "--test-dataset", str(self.phase_inputs_dir / "test_dataset.jsonl"),
            ],
            realtime_output=True
        )
        assert eval_result == 0, f"Evaluation only mode failed with exit code {eval_result}"

        # Verify expected output file exists
        expected_output_file = self.temp_output_dir / "evaluation_results.json"
        assert expected_output_file.exists(), f"Expected evaluation results file not found: {expected_output_file}"

        # Verify content of the output file
        import json
        with open(expected_output_file, 'r') as f:
            data = json.load(f)
            assert isinstance(data, dict), "Evaluation results should be a dictionary"
            assert 'metrics' in data, "Evaluation results should contain 'metrics'"
            assert 'total_examples' in data, "Evaluation results should contain 'total_examples'"
            assert 'detailed_results' in data, "Evaluation results should contain 'detailed_results'"

            metrics = data['metrics']
            assert 'exact_match_accuracy' in metrics, "Metrics should contain 'exact_match_accuracy'"
            assert 'avg_codebleu' in metrics, "Metrics should contain 'avg_codebleu'"

            detailed_results = data['detailed_results']
            assert isinstance(detailed_results, list), "'detailed_results' should be a list"

    def test_upload_only_fails_with_no_adapters(self):
        """Test upload only mode fails with no model directory"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-upload"
            ],
            realtime_output=True
        )
        assert result == 1, f"Upload only mode should fail with no model directory, got exit code {result}"
    
    def test_upload_only_fails_with_no_train_dataset(self):
        """Test upload only mode fails with no training dataset"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-upload",
                "--adapter-input", str(self.phase_inputs_dir / "adapters"),
            ],
            realtime_output=True
        )
        assert result == 1, f"Upload only mode should fail with no training dataset, got exit code {result}"

    def test_upload_only_fails_with_no_validation_dataset(self):
        """Test upload only mode fails with no validation dataset"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-upload",
                "--adapter-input", str(self.phase_inputs_dir / "adapters"),
                "--train-dataset", str(self.phase_inputs_dir / "train_dataset.jsonl"),
            ],
            realtime_output=True
        )
        assert result == 1, f"Upload only mode should fail with no validation dataset, got exit code {result}"

    def test_upload_only_fails_with_no_test_dataset(self):
        """Test upload only mode fails with no test dataset"""
        result = self.run_process_artifacts(
            additional_args=[
                "--only-upload",
                "--adapter-input", str(self.phase_inputs_dir / "adapters"),
                "--train-dataset", str(self.phase_inputs_dir / "train_dataset.jsonl"),
                "--validation-dataset", str(self.phase_inputs_dir / "validation_dataset.jsonl"),
            ],
            realtime_output=True
        )
        assert result == 1, f"Upload only mode should fail with no test dataset, got exit code {result}"

    def test_upload_only_with_adapters_and_datasets(self, test_upload_staging_dir):
        """Test upload only mode with provided model directory and datasets"""
        upload_result = self.run_process_artifacts(
            additional_args=[
                "--only-upload",
                "--adapter-input", str(self.phase_inputs_dir / "adapters"),
                "--train-dataset", str(self.phase_inputs_dir / "train_dataset.jsonl"),
                "--validation-dataset", str(self.phase_inputs_dir / "validation_dataset.jsonl"),
                "--test-dataset", str(self.phase_inputs_dir / "test_dataset.jsonl"),
            ],
            realtime_output=True
        )
        assert upload_result == 0, f"Upload only mode failed with exit code {upload_result}"

        # Verify expected output file exists
        upload_datasets_dirs = list(test_upload_staging_dir.glob("datasets/*"))
        assert len(upload_datasets_dirs) == 1, "No upload datasets directory found in the output directory"

        upload_datasets_dir = upload_datasets_dirs[0]
        assert upload_datasets_dir.exists(), f"Expected upload datasets directory not found: {upload_datasets_dir}"

        upload_datasets_files = list(map(lambda f: f.name, list(upload_datasets_dir.glob("*"))))
        assert "README.md" in upload_datasets_files, "Uploaded train dataset file not found"
        assert "train.jsonl" in upload_datasets_files, "Uploaded train dataset file not found"
        assert "valid.jsonl" in upload_datasets_files, "Uploaded validation dataset file not found"

        upload_model_dirs = list(test_upload_staging_dir.glob("model/*"))
        assert len(upload_model_dirs) == 1, "No upload model directory found in the output directory"

        upload_model_dir = upload_model_dirs[0]
        upload_model_files = list(map(lambda f: f.name, list(upload_model_dir.glob("*"))))
        assert upload_model_dir.exists(), f"Expected upload models directory not found: {upload_model_dir}"

        assert "adapters.safetensors" in upload_model_files, "Uploaded adapters file not found"
        assert "training_metadata.json" in upload_model_files, "Uploaded training metadata file not found"
        assert "README.md" in upload_model_files, "Uploaded model README file not found"
        assert "adapter_config.json" in upload_model_files, "Uploaded adapter_config.json file not found"
        assert "training-recipe.yaml" in upload_model_files, "Uploaded training-recipe.yaml file not found"

        # Verify Model README.md statistics counts are greater than 0
        model_readme_path = upload_model_dir / "README.md"
        with open(model_readme_path, 'r') as f:
            model_readme_content = f.read()

        # Extract and verify model README statistics
        model_total_match = re.search(r'\*\*Total Examples\*\*: ([\d,]+)', model_readme_content)
        model_train_match = re.search(r'\*\*Training Set\*\*: ([\d,]+) examples', model_readme_content)
        model_val_match = re.search(r'\*\*Validation Set\*\*: ([\d,]+) examples', model_readme_content)
        model_high_match = re.search(r'\*\*High Quality\*\*: ([\d,]+) examples', model_readme_content)
        model_low_match = re.search(r'\*\*Low Quality\*\*: ([\d,]+) examples', model_readme_content)

        assert model_total_match, "Model README missing Total Examples statistic"
        assert model_train_match, "Model README missing Training Set statistic"
        assert model_val_match, "Model README missing Validation Set statistic"
        assert model_high_match, "Model README missing High Quality statistic"
        assert model_low_match, "Model README missing Low Quality statistic"

        model_total = int(model_total_match.group(1).replace(',', ''))
        model_train = int(model_train_match.group(1).replace(',', ''))
        model_val = int(model_val_match.group(1).replace(',', ''))
        model_high = int(model_high_match.group(1).replace(',', ''))
        model_low = int(model_low_match.group(1).replace(',', ''))

        assert model_total > 0, f"Model README Total Examples must be > 0, got {model_total}"
        assert model_train > 0, f"Model README Training Set must be > 0, got {model_train}"
        assert model_val > 0, f"Model README Validation Set must be > 0, got {model_val}"
        assert model_high > 0, f"Model README High Quality must be > 0, got {model_high}"
        assert model_low > 0, f"Model README Low Quality must be > 0, got {model_low}"

        # Verify Dataset README.md statistics counts are greater than 0
        dataset_readme_path = upload_datasets_dir / "README.md"
        with open(dataset_readme_path, 'r') as f:
            dataset_readme_content = f.read()

        # Extract and verify dataset README statistics
        dataset_total_match = re.search(r'\*\*Total Examples\*\*: ([\d,]+)', dataset_readme_content)
        dataset_train_match = re.search(r'\*\*Training Split\*\*: ([\d,]+)', dataset_readme_content)
        dataset_val_match = re.search(r'\*\*Validation Split\*\*: ([\d,]+)', dataset_readme_content)
        dataset_high_match = re.search(r'\*\*High Quality\*\*: ([\d,]+) examples', dataset_readme_content)
        dataset_low_match = re.search(r'\*\*Low Quality\*\*: ([\d,]+) examples', dataset_readme_content)

        assert dataset_total_match, "Dataset README missing Total Examples statistic"
        assert dataset_train_match, "Dataset README missing Training Split statistic"
        assert dataset_val_match, "Dataset README missing Validation Split statistic"
        assert dataset_high_match, "Dataset README missing High Quality statistic"
        assert dataset_low_match, "Dataset README missing Low Quality statistic"

        dataset_total = int(dataset_total_match.group(1).replace(',', ''))
        dataset_train = int(dataset_train_match.group(1).replace(',', ''))
        dataset_val = int(dataset_val_match.group(1).replace(',', ''))
        dataset_high = int(dataset_high_match.group(1).replace(',', ''))
        dataset_low = int(dataset_low_match.group(1).replace(',', ''))

        assert dataset_total > 0, f"Dataset README Total Examples must be > 0, got {dataset_total}"
        assert dataset_train > 0, f"Dataset README Training Split must be > 0, got {dataset_train}"
        assert dataset_val > 0, f"Dataset README Validation Split must be > 0, got {dataset_val}"
        assert dataset_high > 0, f"Dataset README High Quality must be > 0, got {dataset_high}"
        assert dataset_low > 0, f"Dataset README Low Quality must be > 0, got {dataset_low}"
