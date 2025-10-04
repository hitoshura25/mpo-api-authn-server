# Implementation Plan: CyberGym Data Extraction Pipeline

## 1. Purpose & Strategic Goal

This document outlines a detailed implementation plan for creating a data extraction pipeline for the CyberGym benchmark.

The **strategic goal** is to produce a state-of-the-art training dataset for our security AI model. While simpler, static datasets (like CVEfixes) provide a good baseline, this pipeline will provide data of the highest possible quality and context.

The **primary benefit** of this approach is that it moves beyond isolated code snippets. By processing the full `git diff` between vulnerable and patched commits from real-world projects, we train our model on the complete context of a fix. This includes multi-line and multi-file changes, which are critical for teaching the model to handle complex, realistic security remediations.

This plan is intended as a follow-on project to the main `process_artifacts.py` refactor and represents the next level of maturity for our model's training data.

---

## 2. Overview of the CyberGym Benchmark

CyberGym is a cybersecurity evaluation framework developed by researchers to test an AI's ability to analyze and reproduce real-world vulnerabilities.

Its data is sourced from over 1,500 historical vulnerabilities in 188 large, open-source projects. For each vulnerability, the framework has access to:

1. The vulnerable (pre-patch) codebase.
2. The fixed (post-patch) codebase.
3. A natural language description of the vulnerability.

This public data provides us with a perfect, high-quality source for creating vulnerability-to-fix training pairs.

---

## 3. The Data Extraction Pipeline: Implementation Details

We will create a new, standalone Python script for this process, for example, `security-ai-analysis/scripts/data-generation/cyber_gym_extractor.py`.

This script will be a one-time or infrequent process that generates a final `cybergym_train_dataset.jsonl` file. This decouples the slow, complex extraction process from the main, faster pipeline runs.

### Step 1: Acquire the Benchmark Metadata

The pipeline starts by acquiring the `tasks.json` file, which contains the metadata for all vulnerability benchmarks.

1. **Action:** Clone the Hugging Face repository containing the metadata.
2. **Command:**
   ```bash
   git lfs install
   git clone https://huggingface.co/datasets/sunblaze-ucb/cybergym ./data/cybergym_metadata
   ```
3. **Key File:** The script will parse `./data/cybergym_metadata/tasks.json`.

### Step 2: Design the Extractor Script

The script will parse `tasks.json` and loop through each vulnerability object in the array. For each object, it will execute the processing loop described in Step 3.

### Step 3: Per-Vulnerability Processing Loop

This is the core logic of the extractor. For each task in `tasks.json`:

1. **Read Task Data:** Extract the `repo_url`, `description`, and `patch_details.commit_id` from the JSON object.

2. **Prepare Environment:** Create a unique temporary directory (e.g., `./tmp/extraction/<repo_name>`) to clone the project into. This prevents conflicts.

3. **Clone Repository:** Execute a `git clone` command using the `repo_url`. The script must include error handling for cases where a repository is no longer accessible.

4. **Identify Commits:**
    * `patched_commit` = The value from `patch_details.commit_id`.
    * `vulnerable_commit` = The parent of the patched commit, which can be referenced in git as `f"{patched_commit}~1"`.

5. **Execute `git diff`:** This is the most critical step. From within the cloned repository's directory, execute the `git diff` command to get the ground truth of the changes.
    * **Command:** `git diff <vulnerable_commit> <patched_commit> > changes.diff`
    * This saves the full, raw diff output to a file.

6. **Parse the Diff:**
    * The script must read the `changes.diff` file.
    * It needs a parser capable of handling the standard diff format to isolate the lines that were removed (prefixed with `-`) and added (prefixed with `+`).
    * This parser must be able to handle changes across multiple files within the same commit.
    * The collection of all lines starting with `-` constitutes the `vulnerable_code`, and all lines starting with `+` constitute the `fixed_code`.

7. **Construct and Save the Training Pair:** Create the final JSON object for our training dataset and append it to the output `.jsonl` file.

8. **Clean Up:** The script must remove the temporary directory containing the cloned repository to conserve disk space.

### Step 4: Structure the Output Data

The script will produce a single output file: `enhanced_datasets/cybergym_train_dataset.jsonl`. Each line in this file will be a JSON object with the following structure:

```json
{
  "instruction": "Based on the following analysis, provide the fix.\n\nAnalysis: [Content from the 'description' field in tasks.json]\n\nVulnerable Code:\n```diff\n- [A line of vulnerable code from the diff]\n- [Another line of vulnerable code]\n```",
  "response": "```diff\n+ [A line of the fixed code from the diff]\n+ [Another line of the fixed code]\n```",
  "metadata": {
    "quality": "high",
    "source": "cybergym",
    "repo_url": "[repo_url from tasks.json]",
    "commit": "[patched_commit]"
  }
}
```

---

## 4. Integration with the Main Pipeline

Once the `cybergym_train_dataset.jsonl` file is generated, integrating it into our main `process_artifacts.py` pipeline is simple:

1. The `public_dataset_loader.py` module (or the `_load_public_dataset` function within the main script) will be modified.
2. Its new, simpler logic will be to just read the pre-generated `cybergym_train_dataset.jsonl` file directly from disk.

This decouples the complex, slow data generation from the much faster training pipeline runs, which is a robust and efficient design.

---

## 5. Estimated Effort & Complexity

* **Effort:** This is a significant engineering task, estimated at 3-5 developer days.
* **Complexity:** High. The script needs to be robust, handle external processes (`git`) safely, manage a file system, and include comprehensive error handling (e.g., for failed clones or invalid diffs).
* **Reward:** The resulting dataset will be of the highest possible quality, providing the necessary context to train a model capable of fixing complex, real-world security vulnerabilities.

---

## 6. Source Links and References

For additional context, the primary resources for the CyberGym project are listed below. These were used as the source for this implementation plan.

* **Official Website:** [https://cybergym.io/](https://cybergym.io/)
* **GitHub Repository:** [https://github.com/sunblaze-ucb/cybergym](https://github.com/sunblaze-ucb/cybergym)
* **Hugging Face Dataset:** [https://huggingface.co/datasets/sunblaze-ucb/cybergym](https://huggingface.co/datasets/sunblaze-ucb/cybergym)
* **Research Paper (arXiv):** [https://arxiv.org/abs/2506.02548](https://arxiv.org/abs/2506.02548)
* **Anthropic Article:** [https://www.anthropic.com/research/building-ai-cyber-defenders](https://www.anthropic.com/research/building-ai-cyber-defenders)
