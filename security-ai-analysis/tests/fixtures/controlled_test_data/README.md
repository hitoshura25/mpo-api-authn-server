# Controlled Test Data for Security AI Analysis

This directory contains minimal, controlled test data with **exactly known vulnerability counts** for regression testing of the security parsing pipeline.

## Test Data Summary

**Total Expected Vulnerabilities: 8**

| Tool | File | Expected Count | Vulnerability Types |
|------|------|----------------|-------------------|
| Semgrep | `semgrep.sarif` | 3 | CWE-798 (hardcoded password), CWE-89 (SQL injection), CWE-79 (XSS) |
| Trivy | `trivy-results.sarif` | 2 | CVE-2024-0001 (lodash), CVE-2024-0002 (express) |
| Checkov | `checkov-results.sarif` | 1 | CKV_AWS_20 (S3 bucket insecure ACL) |
| OSV Scanner | `osv-results.json` | 1 | GHSA-j8r2-6x86-q33q (requests proxy auth) |
| ZAP | `zap-report.json` | 1 | 10035 (HSTS header missing) |

## Expected Parser Results

### Semgrep Parser (`parse_semgrep_sarif`)
```python
assert len(results) == 3
assert results[0]['id'] == 'test.hardcoded-password'
assert results[0]['file_path'] == 'test-config.js'
assert results[0]['severity'] == 'HIGH'
assert results[0]['start']['line'] == 15
```

### Trivy Parser (`parse_trivy_json`)
```python
assert len(results) == 2
assert results[0]['id'] == 'CVE-2024-0001'
assert results[0]['package'] == 'lodash'
assert results[0]['severity'] == 'HIGH'
assert results[0]['path'] == 'package-lock.json'
```

### Checkov Parser (`parse_checkov_json`)
```python
assert len(results) == 1
assert results[0]['id'] == 'CKV_AWS_20'
assert results[0]['path'] == 'terraform/s3.tf'
assert results[0]['start']['line'] == 15
```

### OSV Scanner Parser (`parse_osv_json`)
```python
assert len(results) == 1
assert results[0]['id'] == 'GHSA-j8r2-6x86-q33q'
assert results[0]['package_name'] == 'requests'
assert results[0]['ecosystem'] == 'PyPI'
assert results[0]['path'] == 'requirements.txt'
```

### ZAP Parser (`parse_zap_json`)
```python
assert len(results) == 1
assert results[0]['id'] == '10035'
assert results[0]['severity'] == 'LOW'
assert results[0]['site_host'] == 'localhost'
assert results[0]['path'] == 'http://localhost:8080/'
```

## Integration Test Expectations

When running `process_artifacts.py` with this controlled test data:

- **Total vulnerabilities parsed**: 8
- **Summary file** (`olmo_analysis_summary.json`):
  ```json
  {
    "total_analyzed": 8,
    "by_tool": {
      "semgrep": 3,
      "trivy": 2,
      "checkov": 1,
      "osv-scanner": 1,
      "zap": 1
    }
  }
  ```
- **Dataset files**: `train.jsonl` (~6 entries), `validation.jsonl` (~2 entries)
- **Narrativized dataset**: `narrativized_dataset.json` (8 entries)

## Purpose

This controlled test data enables:
1. **Exact assertions** instead of vague `> 0` checks
2. **Regression detection** - any parser returning wrong count = test failure
3. **Fast testing** - minimal files parse quickly
4. **Predictable results** - same input always produces same output
5. **Comprehensive coverage** - all security tools represented

## Usage in Tests

```python
# Unit test example
def test_semgrep_parser_exact_count():
    results = parse_semgrep_sarif('controlled_test_data/semgrep.sarif')
    assert len(results) == 3
    # Additional assertions for specific fields...

# Integration test example
def test_exact_vulnerability_parsing():
    # Run process_artifacts.py with controlled test data
    # Assert total vulnerabilities == 8
    # Assert by_tool counts match exactly
```