# Refactoring Plan for `process_artifacts.py`

## 1. Executive Summary

This document outlines a detailed plan to refactor the `process_artifacts.py` script. The goal is to streamline the existing complex pipeline, significantly improve the quality of the AI model's training data, and sharpen the model's focus on its primary task: generating security vulnerability fixes.

The core of this refactor is to shift from a pipeline that primarily generates descriptive narratives to one that constructs a rich, high-quality dataset from multiple sources, including public datasets and project-specific, deterministic fixes.

## 2. Core Architectural Changes

The current 8+ phase architecture will be consolidated into a cleaner, more linear 5-phase pipeline. This reduces complexity, eliminates redundant intermediate files, and makes the workflow more intuitive.

**The New 5-Phase Pipeline:**

1.  **Phase 1: Parse & Categorize:** Ingest raw security scan reports and immediately categorize each vulnerability by security domain.
2.  **Phase 2: Analyze & Narrate:** Use the AI model (with RAG) to analyze the categorized vulnerabilities and generate a human-readable narrative for each.
3.  **Phase 3: Construct Datasets:** The new heart of the pipeline. It aggregates training data from three distinct sources to create a high-quality, mixed dataset.
4.  **Phase 4: Train Model:** Fine-tune the model on the new dataset, using quality weighting to prioritize learning from real fixes.
5.  **Phase 5: Upload Artifacts:** Upload the final model and datasets to the Hugging Face Hub.

---

## 3. Detailed Phase-by-Phase Implementation Plan

### Phase 1: Parse & Categorize

*   **New Function:** `phase_1_parse_and_categorize()`
*   **Replaces:** `parse_vulnerabilities_phase()`, and the categorization logic from `analysis_summary_phase()`.
*   **Input:** Directory of security scan files (e.g., `data/security_artifacts/extracted/`).
*   **Output:** A single file: `results/1_categorized_vulnerabilities.json`.
*   **Logic:**
    1.  Find all security scan files (`trivy`, `zap`, `semgrep`, etc.).
    2.  Parse the vulnerabilities from each file using the existing parser modules.
    3.  Immediately after parsing, instantiate `VulnerabilityCategorizor`.
    4.  Run the categorizer on the newly parsed vulnerabilities, adding the `security_category` and `category_confidence` fields directly to each vulnerability object.
    5.  Aggregate all categorized vulnerabilities into a single list and save to the output JSON file.

### Phase 2: Analyze & Narrate

*   **New Function:** `phase_2_analyze_and_narrate()`
*   **Replaces:** `core_analysis_phase()`, `rag_enhancement_phase()`, `analysis_summary_phase()`, `narrativization_phase()`.
*   **Input:** The path to `results/1_categorized_vulnerabilities.json`.
*   **Output:** A single file: `results/2_narrativized_analyses.json`.
*   **Logic:**
    1.  Initialize the `RAGEnhancedOLMoAnalyzer` and `SecurityNarrativizer` once.
    2.  Load the list of categorized vulnerabilities from the input file.
    3.  For each vulnerability:
        a.  Perform URL-to-code mapping if it's a ZAP/DAST finding.
        b.  Use the RAG-enhanced analyzer to get the AI analysis.
        c.  Use the `SecurityNarrativizer` to generate the descriptive narrative.
    4.  Create a new JSON object for each vulnerability containing: the original vulnerability data, its category, the AI analysis, and the generated narrative.
    5.  Save the list of these complete objects to the output file.

### Phase 3: Construct Datasets

*   **New Function:** `phase_3_construct_datasets()`
*   **Replaces:** The old `datasets_phase()`.
*   **Input:** The path to `results/2_narrativized_analyses.json`.
*   **Output:** `results/3_train_dataset.jsonl` and `results/3_validation_dataset.jsonl`.
*   **Logic:**
    1.  **Source 1: Load Public Data.**
        *   Call a new helper function, `_load_public_dataset()`, which will use the `public_dataset_loader.py` module.
        *   This loader will download and parse the **CVEfixes dataset**, transforming it into `instruction`/`response` pairs where the `response` is the fixed code.
        *   Add `metadata: {'quality': 'high', 'source': 'public'}` to each pair.
    2.  **Source 2: Generate Specific Fixes.**
        *   Call a new helper function, `_generate_specific_fixes()`, that takes the list of narrativized analyses as input.
        *   This function will identify vulnerabilities with deterministic fixes (e.g., Trivy/OSV dependency upgrades) and generate precise `instruction`/`response` pairs.
        *   Add `metadata: {'quality': 'high', 'source': 'generated'}` to each pair.
    3.  **Source 3: Process AI Narratives (Pivoted Role).**
        *   Iterate through the narrativized analyses. For each, create a training pair where the **narrative is part of the `instruction`**.
        *   If a known fix exists (from Source 2), the `response` is that fix.
        *   If no known fix exists, the `response` can be the AI analysis text, but the pair is marked as low quality.
        *   Add `metadata: {'quality': 'low', 'source': 'narrative'}` to these pairs.
    4.  **Combine and Split.**
        *   Aggregate the training pairs from all three sources into a single list.
        *   Shuffle the list and split it into training (80%) and validation (20%) sets.
        *   Save the final datasets as `.jsonl` files.

### Phase 4: Train Model

*   **New Function:** `phase_4_train_model()`
*   **Replaces:** `training_phase()`.
*   **Input:** Paths to `3_train_dataset.jsonl` and `3_validation_dataset.jsonl`.
*   **Output:** Path to the fine-tuned model artifacts.
*   **Logic:**
    1.  The function's logic remains similar, initiating the training process.
    2.  **CRITICAL:** The underlying training script (e.g., `sequential_pipeline_integration.py`) must be modified to read the `quality` field from the dataset's metadata.
    3.  Implement **quality-weighted sampling**, where examples with `quality: 'high'` are sampled more frequently during training epochs. This ensures the model learns preferentially from real fixes.

### Phase 5: Upload Artifacts

*   **New Function:** `phase_5_upload_artifacts()`
*   **Replaces:** `upload_phase()`.
*   **Input:** Path to the fine-tuned model artifacts and the dataset files.
*   **Output:** Status of the upload.
*   **Logic:** The logic can remain largely the same, handling the upload of the model and the newly generated high-quality datasets to the Hugging Face Hub.

---

## 4. Key Data Structure Change: The Training Pair

This refactor fundamentally changes the structure and philosophy of the training data.

**Old Structure (Narrative as Response):**
```json
{
  "instruction": "Analyze this security vulnerability: { 'id': 'CVE-2021-44228', 'tool': 'trivy', ... }",
  "response": "A critical remote code execution vulnerability, Log4Shell, exists in Apache Log4j...",
  "metadata": {}
}
```

**New Structure (Narrative as Context for a Fix):**
```json
{
  "instruction": "Based on the following analysis, provide the fix.\n\nAnalysis: A critical remote code execution vulnerability, Log4Shell, exists in Apache Log4j...\n\nVulnerable Code: <dependency>...</dependency>",
  "response": "<dependency>...<version>2.17.1</version>...</dependency>",
  "metadata": {
    "quality": "high",
    "source": "public"
  }
}
```

---

## 5. New Module Dependencies

*   **`public_dataset_loader.py`:** A new file required to handle the download and parsing of public datasets like CVEfixes. This module will be called by `phase_3_construct_datasets`.

---

## 6. `main()` Orchestrator Refactor

The `main()` function will be simplified to a clean, linear set of calls, making the entire process easy to follow.

**New `main()` structure:**
```python
def main():
    # Argument parsing and setup
    args = parse_arguments()
    
    # Execute the streamlined pipeline
    print("🚀 Starting Phase 1: Parse & Categorize")
    categorized_vulns_file = phase_1_parse_and_categorize(args.artifacts_dir, args.output_dir)
    
    print("🚀 Starting Phase 2: Analyze & Narrate")
    narratives_file = phase_2_analyze_and_narrate(categorized_vulns_file, args.output_dir)

    print("🚀 Starting Phase 3: Construct Datasets")
    train_file, val_file = phase_3_construct_datasets(narratives_file, args.output_dir)

    print("🚀 Starting Phase 4: Train Model")
    model_path = phase_4_train_model(train_file, val_file, args)

    print("🚀 Starting Phase 5: Upload Artifacts")
    if not args.skip_upload:
        phase_5_upload_artifacts(model_path, [train_file, val_file], args)

    print("\n✅ Pipeline completed successfully!")
```