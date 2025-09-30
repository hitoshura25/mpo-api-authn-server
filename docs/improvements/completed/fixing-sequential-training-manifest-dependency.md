# Fixing the Sequential Training Manifest Dependency Issue

**Status**: Proposed
**Created**: 2025-09-29

## 1. Summary

The integration test `test_training_phase_creates_complete_model_files` is legitimately failing. It has exposed a critical race condition in the sequential fine-tuning pipeline (`sequential_fine_tuner.py`). The pipeline fails because Stage 2 of the training process depends on the results of Stage 1, which it tries to locate by reading the `run-manifest.json`. However, the current implementation only writes the results of *both* stages to the manifest after the entire pipeline has completed.

This document outlines the root cause of this failure and proposes two effective solutions to resolve it.

## 2. Root Cause Analysis

The sequential fine-tuning process consists of two main stages:
1.  **Stage 1:** Trains a "Vulnerability Analysis Specialist" model.
2.  **Stage 2:** Trains a "Code Fix Generation Specialist" model, building upon the knowledge of the Stage 1 model.

To prevent "catastrophic forgetting," Stage 2 requires access to the training data used in Stage 1. The new structured output architecture correctly dictates that the path to this data should be discovered by reading the `run-manifest.json` file.

### The Dependency Conflict

The logical flow of the `sequential_fine_tune` method is currently as follows:
1.  Run Stage 1 training.
2.  Run Stage 2 training.
3.  Update the `run-manifest.json` with the results of both Stage 1 and Stage 2.

The conflict arises at the beginning of step 2. The Stage 2 process attempts to read `run-manifest.json` to find the path to the Stage 1 training data. Since the manifest has not yet been updated, the path is not found, and the process correctly raises a `FileNotFoundError` to halt the run.

The test `test_training_phase_creates_complete_model_files` correctly triggers this exact scenario, making it a valid and important test that has successfully identified a bug in the application's control flow.

## 3. Proposed Solutions

Both of the following approaches will fix the bug. They represent a trade-off between a direct, tactical fix and a more robust, architectural one.

### Approach A: Incremental Manifest Updates

This approach involves modifying the pipeline to save the results of each stage to the manifest as soon as the stage is complete.

#### Implementation

1.  **Split the update function:** Refactor the single `_update_training_run_manifest` function in `sequential_fine_tuner.py` into two separate, smaller functions:
    *   `_update_manifest_after_stage1(stage1_result, ...)`
    *   `_update_manifest_after_stage2(stage2_result, ...)`

2.  **Update the control flow:** Modify the `sequential_fine_tune` method to call these new functions immediately after each stage completes.

    ```python
    # In sequential_fine_tuner.py

    def sequential_fine_tune(...):
        # ...
        # Run Stage 1 and get the results
        stage1_result = self._train_stage1_analysis(...)
        
        # **FIX: Update and save the manifest immediately after Stage 1**
        self._update_manifest_after_stage1(stage1_result, ...)

        # Run Stage 2, which can now read the updated manifest
        stage2_result = self._train_stage2_codefix(...)

        # **Update the manifest with Stage 2 results**
        self._update_manifest_after_stage2(stage2_result, ...)
        # ...
    ```

#### Pros & Cons
*   **Pro:** This is a direct, pragmatic fix that requires minimal refactoring and cleanly resolves the dependency issue.
*   **Con:** The manifest is not a complete "plan" at the start of the run. It is built up as the process executes, which is slightly less robust for external monitoring or debugging tools.

### Approach B: Upfront Manifest Generation (Recommended)

This approach aligns with the principles of the new structured output architecture by treating the manifest as a complete "contract" for the training run from the very beginning, while maintaining simplicity and fail-fast behavior.

#### Implementation

1.  **Modify `TrainingRun` Creation:** When a `TrainingRun` object is first created (e.g., in `training_run_manager.py`), its `create_run` method should be responsible for:
    *   Generating and saving a `run-manifest.json` that is **fully populated with all the predefined, relative paths** for all artifacts that will be created during the run.
    *   **No upfront directory creation** - let each stage create its own directories when needed.
    *   **No status tracking** - use fail-fast philosophy instead.

2.  **Pure Path Contract:** The manifest serves a single purpose: defining where each stage should write its outputs.

    ```json
    {
      "run_metadata": {
        "run_id": "webauthn-security-20250929_120000",
        "timestamp": "2025-09-29T12:00:00Z",
        "base_model": "OLMo-2-1B-mlx-q4"
      },
      "stage1": {
        "adapters_path": "./stage1/adapters/",
        "merged_model_path": "./stage1/merged-model/",
        "training_data_path": "./stage1/training-data/analysis-dataset.jsonl"
      },
      "stage2": {
        "final_model_path": "./stage2/final-model/",
        "training_data_paths": {
          "mixed_dataset": "./stage2/training-data/mixed-dataset.jsonl"
        }
      }
    }
    ```

3.  **Lazy Directory Creation & Fail-Fast:** Each stage reads paths from the manifest, creates its own directories when it starts, and writes artifacts. If Stage 2 needs Stage 1 artifacts and they don't exist, the system fails immediately - no status checking needed.

#### Pros & Cons
*   **Pro:** Architecturally robust with contract-first design that eliminates race conditions by design.
*   **Pro:** No storage waste from unused directories - directories created only when stages actually run.
*   **Pro:** Simpler implementation without status management complexity.
*   **Pro:** Perfect alignment with fail-fast philosophy - missing artifacts cause immediate failure.
*   **Pro:** Natural error handling - artifact existence indicates stage completion.
*   **Con:** Requires moderate refactoring in `TrainingRunManager` and `SequentialFineTuner`.

## 4. Recommendation

**Approach B (Upfront Manifest Generation) is the recommended solution.**

While Approach A is a valid and quicker fix, Approach B provides a more significant, long-term improvement. It fully embraces the "contract-first" design of the structured output architecture, leading to a more predictable, robust, and maintainable system. It eliminates race conditions by design rather than by ordering operations.

## 5. Action Plan (for Approach B)

1.  **Modify `TrainingRunManager.create_run`** to generate and save a complete manifest with all predefined paths (no status fields, no directory creation).
2.  **Update `SequentialFineTuner`** to read paths from the manifest and create directories when each stage runs.
3.  **Remove `_update_training_run_manifest` function entirely** - no status updates needed with fail-fast philosophy.
4.  **Implement fail-fast behavior** where Stage 2 checks for Stage 1 artifacts existence and fails immediately if missing.
5.  **Verify** that the `test_training_phase_creates_complete_model_files` test passes after these changes.
