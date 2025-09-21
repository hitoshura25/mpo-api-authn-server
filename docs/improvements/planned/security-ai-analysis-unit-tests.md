# Security AI Analysis Unit Testing Implementation Plan

## Overview

This document provides a comprehensive implementation plan for adding unit testing to the `security-ai-analysis` pipeline, with a focus on testing the actual `process_artifacts.py` script that users run. The goal is to catch regressions like the recent semgrep SARIF parsing issue that returned 0 vulnerabilities when 107 were expected.

## Problem Statement

The current `security-ai-analysis` pipeline lacks automated testing, leading to:
- **Regression Issues**: Changes break existing functionality without detection (e.g., semgrep SARIF parsing returning 0 results)
- **Debugging Difficulty**: No systematic way to verify each component works correctly
- **User Impact**: Users experience broken functionality when running `process_artifacts.py`

**Key Insight**: We must test the actual `process_artifacts.py` script that users run, not just individual components in isolation.

## Architecture Overview

### Current File Structure
```
security-ai-analysis/
├── process_artifacts.py          # Main user-facing script
├── parsers/
│   ├── semgrep_parser.py
│   ├── sarif_parser.py
│   ├── trivy_parser.py
│   ├── checkov_parser.py
│   ├── osv_parser.py
│   └── zap_parser.py
├── enhanced_dataset_creator.py
├── vulnerable_code_extractor.py
├── multi_approach_fix_generator.py
└── data/security_artifacts/       # Real vulnerability data
```

### Proposed Testing Structure
```
security-ai-analysis/
├── tests/
│   ├── integration/
│   │   ├── test_process_artifacts_script.py     # Main integration tests
│   │   ├── test_vulnerability_count_regression.py
│   │   └── test_enhanced_dataset_e2e.py
│   ├── unit/
│   │   ├── test_file_discovery.py
│   │   └── test_parser_interfaces.py
│   ├── fixtures/
│   │   ├── sample_security_artifacts/           # Test data
│   │   │   ├── semgrep-results/
│   │   │   │   ├── semgrep.sarif
│   │   │   │   └── semgrep-results.json
│   │   │   ├── trivy-results/
│   │   │   └── checkov-results/
│   │   └── expected_outputs/
│   │       ├── expected_summary.json
│   │       └── expected_enhanced_dataset.jsonl
│   ├── baselines/
│   │   └── vulnerability_counts.json           # Regression baselines
│   ├── conftest.py                             # Pytest configuration
│   └── requirements.txt                        # Test dependencies
├── pytest.ini                                  # Pytest settings
└── [existing files...]
```

## Implementation Plan

### Phase 1: Core Integration Testing Infrastructure

#### 1.1 Create Test Directory Structure

**Create the following directories:**
```bash
cd security-ai-analysis
mkdir -p tests/{integration,unit,fixtures,baselines}
mkdir -p tests/fixtures/{sample_security_artifacts,expected_outputs}
```

#### 1.2 Set up Pytest Configuration

**File: `tests/conftest.py`**
```python
"""
Pytest configuration and shared fixtures for security-ai-analysis tests.
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_artifacts_dir():
    """Path to sample security artifacts for testing."""
    return Path(__file__).parent / "fixtures" / "sample_security_artifacts"


@pytest.fixture
def expected_baseline_counts():
    """Expected vulnerability counts for regression testing."""
    return {
        "semgrep": 107,
        "trivy": 168,
        "checkov": 10,
        "osv": 46,
        "zap": 9
    }


@pytest.fixture
def process_artifacts_args():
    """Standard arguments for process_artifacts.py testing."""
    return [
        "--skip-fine-tuning",  # Speed up tests
        "--disable-rag",       # Avoid RAG complexity in tests
        "--disable-sequential-fine-tuning"
    ]
```

**File: `pytest.ini`**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
markers =
    integration: Integration tests that run the full script
    regression: Regression protection tests
    slow: Tests that take longer to run
```

**File: `tests/requirements.txt`**
```
pytest>=7.0.0
pytest-mock>=3.8.0
pytest-timeout>=2.1.0
```

#### 1.3 Create Sample Test Data

**Critical**: Copy current working security artifacts to create test fixtures:

```bash
# Copy current working data as test fixtures
cp -r data/security_artifacts tests/fixtures/sample_security_artifacts/
```

This ensures tests use known-good data that matches current expectations.

### Phase 2: Main Integration Tests

#### 2.1 Core Script Integration Test

**File: `tests/integration/test_process_artifacts_script.py`**
```python
"""
Integration tests for the main process_artifacts.py script.
These tests run the actual script that users execute.
"""
import subprocess
import json
import pytest
from pathlib import Path


class TestProcessArtifactsScript:
    """Test the actual process_artifacts.py script execution."""

    def test_script_runs_successfully(self, sample_artifacts_dir, temp_output_dir, process_artifacts_args):
        """Test that the script runs without errors."""
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(sample_artifacts_dir),
            "--output-dir", str(temp_output_dir)
        ] + process_artifacts_args

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        assert "Processing complete!" in result.stdout, "Script did not complete successfully"

    def test_expected_output_files_created(self, sample_artifacts_dir, temp_output_dir, process_artifacts_args):
        """Test that all expected output files are created."""
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(sample_artifacts_dir),
            "--output-dir", str(temp_output_dir)
        ] + process_artifacts_args

        subprocess.run(cmd, check=True, capture_output=True, cwd=Path(__file__).parent.parent.parent)

        # Check required output files exist
        expected_files = [
            "olmo_analysis_summary.json",
            "olmo_analysis_results.json",
            "narrativized_dataset.json",
            "train.jsonl",
            "validation.jsonl"
        ]

        for filename in expected_files:
            output_file = temp_output_dir / filename
            assert output_file.exists(), f"Expected output file missing: {filename}"
            assert output_file.stat().st_size > 0, f"Output file is empty: {filename}"

    @pytest.mark.regression
    def test_vulnerability_counts_match_baseline(self, sample_artifacts_dir, temp_output_dir,
                                                expected_baseline_counts, process_artifacts_args):
        """Regression test: Ensure vulnerability counts don't drop unexpectedly."""
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(sample_artifacts_dir),
            "--output-dir", str(temp_output_dir)
        ] + process_artifacts_args

        subprocess.run(cmd, check=True, capture_output=True, cwd=Path(__file__).parent.parent.parent)

        # Load the analysis summary
        summary_file = temp_output_dir / "olmo_analysis_summary.json"
        with open(summary_file) as f:
            summary = json.load(f)

        # Check vulnerability counts against baseline
        actual_by_tool = summary.get("by_tool", {})

        for tool, expected_min_count in expected_baseline_counts.items():
            actual_count = actual_by_tool.get(tool, 0)
            assert actual_count >= expected_min_count, \
                f"Regression detected for {tool}: expected >= {expected_min_count}, got {actual_count}"

        # Check total count
        total_expected = sum(expected_baseline_counts.values())
        actual_total = summary.get("total_analyzed", 0)
        assert actual_total >= total_expected, \
            f"Total vulnerability count regression: expected >= {total_expected}, got {actual_total}"

    def test_semgrep_sarif_parsing_specific(self, sample_artifacts_dir, temp_output_dir, process_artifacts_args):
        """Specific regression test for semgrep SARIF parsing issue."""
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(sample_artifacts_dir),
            "--output-dir", str(temp_output_dir)
        ] + process_artifacts_args

        subprocess.run(cmd, check=True, capture_output=True, cwd=Path(__file__).parent.parent.parent)

        # Load summary and check semgrep specifically
        summary_file = temp_output_dir / "olmo_analysis_summary.json"
        with open(summary_file) as f:
            summary = json.load(f)

        # This test specifically catches the semgrep SARIF issue
        semgrep_count = summary.get("by_tool", {}).get("semgrep", 0)
        assert semgrep_count > 0, "Semgrep SARIF parsing returned 0 vulnerabilities - regression detected"
        assert semgrep_count >= 100, f"Semgrep count too low: expected >= 100, got {semgrep_count}"
```

#### 2.2 Enhanced Dataset Integration Test

**File: `tests/integration/test_enhanced_dataset_e2e.py`**
```python
"""
End-to-end tests for enhanced dataset creation functionality.
"""
import subprocess
import json
import pytest
from pathlib import Path


class TestEnhancedDatasetEndToEnd:
    """Test enhanced dataset creation through the full pipeline."""

    def test_enhanced_dataset_created(self, sample_artifacts_dir, temp_output_dir, process_artifacts_args):
        """Test that enhanced dataset files are created."""
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(sample_artifacts_dir),
            "--output-dir", str(temp_output_dir)
        ] + process_artifacts_args

        subprocess.run(cmd, check=True, capture_output=True, cwd=Path(__file__).parent.parent.parent)

        # Check enhanced dataset directory exists
        enhanced_dir = Path("enhanced_datasets/code-aware-training")
        assert enhanced_dir.exists(), "Enhanced dataset directory not created"

        # Check for enhanced dataset files
        enhanced_files = list(enhanced_dir.glob("enhanced_train_*.jsonl"))
        assert enhanced_files, "No enhanced dataset JSONL files created"

        # Verify content structure
        with open(enhanced_files[0]) as f:
            first_line = f.readline()
            example = json.loads(first_line)

            assert "instruction" in example, "Enhanced dataset missing instruction field"
            assert "response" in example, "Enhanced dataset missing response field"
            assert "metadata" in example, "Enhanced dataset missing metadata field"

    def test_code_aware_examples_present(self, sample_artifacts_dir, temp_output_dir, process_artifacts_args):
        """Test that code-aware examples are actually generated."""
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(sample_artifacts_dir),
            "--output-dir", str(temp_output_dir)
        ] + process_artifacts_args

        subprocess.run(cmd, check=True, capture_output=True, cwd=Path(__file__).parent.parent.parent)

        # Find enhanced dataset files
        enhanced_dir = Path("enhanced_datasets/code-aware-training")
        enhanced_files = list(enhanced_dir.glob("enhanced_train_*.jsonl"))

        # Check for code-specific content
        code_examples_found = False
        with open(enhanced_files[0]) as f:
            for line in f:
                example = json.loads(line)
                instruction = example["instruction"].lower()

                # Look for code-specific language
                if any(lang in instruction for lang in ["kotlin", "java", "typescript", "security vulnerability"]):
                    if any(keyword in instruction for keyword in ["line", "function", "class", "file"]):
                        code_examples_found = True
                        break

        assert code_examples_found, "No code-aware examples found in enhanced dataset"
```

### Phase 3: Regression Protection System

#### 3.1 Baseline Management

**File: `tests/integration/test_vulnerability_count_regression.py`**
```python
"""
Regression protection system for vulnerability counts.
"""
import subprocess
import json
import pytest
from pathlib import Path


class TestVulnerabilityCountRegression:
    """Protect against regressions in vulnerability processing."""

    def test_establish_or_verify_baselines(self, sample_artifacts_dir, temp_output_dir, process_artifacts_args):
        """Establish baselines on first run, verify on subsequent runs."""
        baseline_file = Path(__file__).parent.parent / "baselines" / "vulnerability_counts.json"

        # Run the script
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(sample_artifacts_dir),
            "--output-dir", str(temp_output_dir)
        ] + process_artifacts_args

        result = subprocess.run(cmd, check=True, capture_output=True, cwd=Path(__file__).parent.parent.parent)

        # Get current counts
        summary_file = temp_output_dir / "olmo_analysis_summary.json"
        with open(summary_file) as f:
            summary = json.load(f)

        current_counts = {
            "total_analyzed": summary.get("total_analyzed", 0),
            "successful": summary.get("successful", 0),
            "by_tool": summary.get("by_tool", {}),
            "by_severity": summary.get("by_severity", {})
        }

        if baseline_file.exists():
            # Verify against existing baseline
            with open(baseline_file) as f:
                baseline = json.load(f)

            # Check total counts
            assert current_counts["total_analyzed"] >= baseline["total_analyzed"] * 0.9, \
                f"Total analyzed dropped significantly: {baseline['total_analyzed']} → {current_counts['total_analyzed']}"

            # Check per-tool counts
            for tool, baseline_count in baseline["by_tool"].items():
                current_count = current_counts["by_tool"].get(tool, 0)
                min_acceptable = baseline_count * 0.9  # 10% tolerance

                assert current_count >= min_acceptable, \
                    f"Tool {tool} count regression: {baseline_count} → {current_count} (min: {min_acceptable})"

        else:
            # First run - establish baseline
            baseline_file.parent.mkdir(parents=True, exist_ok=True)
            with open(baseline_file, 'w') as f:
                json.dump(current_counts, f, indent=2)

            print(f"Baseline established: {baseline_file}")

    def test_no_zero_counts_regression(self, sample_artifacts_dir, temp_output_dir, process_artifacts_args):
        """Ensure no tool returns zero vulnerabilities when it shouldn't."""
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(sample_artifacts_dir),
            "--output-dir", str(temp_output_dir)
        ] + process_artifacts_args

        subprocess.run(cmd, check=True, capture_output=True, cwd=Path(__file__).parent.parent.parent)

        summary_file = temp_output_dir / "olmo_analysis_summary.json"
        with open(summary_file) as f:
            summary = json.load(f)

        by_tool = summary.get("by_tool", {})

        # Tools that should never return zero (based on current artifacts)
        expected_tools = ["semgrep", "trivy", "checkov"]

        for tool in expected_tools:
            count = by_tool.get(tool, 0)
            assert count > 0, f"Tool {tool} returned zero vulnerabilities - likely a parsing regression"
```

### Phase 4: Unit Tests for Critical Components

#### 4.1 File Discovery Testing

**File: `tests/unit/test_file_discovery.py`**
```python
"""
Unit tests for security file discovery logic.
"""
import pytest
import tempfile
import shutil
from pathlib import Path

# Import the function to test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from process_artifacts import find_security_files


class TestFileDiscovery:
    """Test the find_security_files function."""

    @pytest.fixture
    def temp_artifacts_dir(self):
        """Create a temporary artifacts directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_semgrep_file_detection(self, temp_artifacts_dir):
        """Test that semgrep files are correctly detected."""
        # Create test files
        semgrep_dir = temp_artifacts_dir / "semgrep-results"
        semgrep_dir.mkdir()

        (semgrep_dir / "semgrep.sarif").write_text('{"version": "2.1.0"}')
        (semgrep_dir / "semgrep-results.json").write_text('{"results": []}')

        scan_files = find_security_files(str(temp_artifacts_dir))

        # Should prefer SARIF over JSON
        assert len(scan_files["semgrep"]) == 1
        assert scan_files["semgrep"][0].endswith("semgrep.sarif")

    def test_all_tool_types_detected(self, temp_artifacts_dir):
        """Test that all expected tool types are detected."""
        # Create test files for each tool
        tools_and_files = {
            "trivy": "trivy-results.sarif",
            "checkov": "checkov-results.sarif",
            "osv": "osv-results.json",
            "zap": "zap-report.json",
            "gitleaks": "gitleaks-results.sarif"
        }

        for tool, filename in tools_and_files.items():
            tool_dir = temp_artifacts_dir / f"{tool}-dir"
            tool_dir.mkdir()
            (tool_dir / filename).write_text('{"dummy": "data"}')

        scan_files = find_security_files(str(temp_artifacts_dir))

        for tool in tools_and_files.keys():
            assert len(scan_files[tool]) == 1, f"Tool {tool} not detected"
```

### Phase 5: Running and Maintenance

#### 5.1 Test Execution Commands

**Run all tests:**
```bash
cd security-ai-analysis
python -m pytest tests/ -v
```

**Run only regression tests:**
```bash
python -m pytest tests/ -m regression -v
```

**Run only integration tests:**
```bash
python -m pytest tests/integration/ -v
```

**Run specific test:**
```bash
python -m pytest tests/integration/test_process_artifacts_script.py::TestProcessArtifactsScript::test_semgrep_sarif_parsing_specific -v
```

#### 5.2 Continuous Integration Integration

**Add to GitHub Actions workflow:**
```yaml
name: Security Analysis Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd security-ai-analysis
          pip install -r requirements.txt
          pip install -r tests/requirements.txt
      - name: Run integration tests
        run: |
          cd security-ai-analysis
          python -m pytest tests/integration/ -v
      - name: Run regression tests
        run: |
          cd security-ai-analysis
          python -m pytest tests/ -m regression -v
```

## Implementation Checklist

### Phase 1 Setup
- [ ] Create test directory structure
- [ ] Copy current security artifacts to `tests/fixtures/sample_security_artifacts/`
- [ ] Create `conftest.py` with fixtures
- [ ] Create `pytest.ini` configuration
- [ ] Install test dependencies

### Phase 2 Core Tests
- [ ] Implement `test_process_artifacts_script.py`
- [ ] Implement `test_enhanced_dataset_e2e.py`
- [ ] Verify tests catch current semgrep SARIF issue
- [ ] Test with known good and bad data

### Phase 3 Regression Protection
- [ ] Implement baseline system
- [ ] Create initial vulnerability count baselines
- [ ] Add zero-count regression protection
- [ ] Test baseline update mechanisms

### Phase 4 Unit Tests
- [ ] Implement file discovery tests
- [ ] Add parser interface tests
- [ ] Test edge cases and error conditions

### Phase 5 Integration
- [ ] Add test execution scripts
- [ ] Set up CI integration
- [ ] Document test execution procedures
- [ ] Train team on test maintenance

## Success Criteria

1. **Regression Detection**: Tests catch issues like the semgrep SARIF parsing returning 0 vulnerabilities
2. **User Experience**: Tests verify the actual `process_artifacts.py` script that users run
3. **Baseline Protection**: Automatic detection when vulnerability counts drop unexpectedly
4. **Fast Feedback**: Tests run quickly enough for regular development use
5. **Maintainable**: New team members can understand and extend the test suite

## Future Enhancements

1. **Performance Testing**: Add tests for processing speed and memory usage
2. **Error Condition Testing**: Comprehensive testing of malformed input handling
3. **Integration with MLX**: Test fine-tuning pipeline components
4. **Quality Metrics**: Test enhanced dataset quality assessment
5. **Cross-Platform Testing**: Ensure tests work on different operating systems

This implementation plan provides a comprehensive testing strategy that focuses on the actual user experience while protecting against regressions like the current semgrep parsing issue.