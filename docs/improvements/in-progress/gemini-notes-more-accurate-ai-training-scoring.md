Properly scoring your "self-healing" model requires a multi-faceted approach to ensure its fixes are not only accurate but also safe and effective. You need to go beyond simple text matching and verify that the model's output is functionally correct and actually resolves the security issue.

Here’s how you can create a robust scoring process.

# Curate a Dedicated Test Set 🧪

First, you must set aside a portion of your vulnerability-fix dataset (e.g., 10-15%) that the model *never sees during training*. This is your *held-out test set*, and it serves as an unbiased benchmark for evaluating the model's performance on new, unseen problems.

# Automated Code Evaluation Metrics

These metrics provide a quantitative score for your model's performance.

- Exact Match Accuracy: This is the simplest metric. It measures the percentage of times the model's generated code is identical, character-for-character, to the ground truth fix in your test set. It's a good starting point but often too strict, as there can be multiple valid ways to fix a piece of code.
  Exact Match Accuracy = Number of Perfect Predictions / Total Predictions

- CodeBLEU Score: This is a more sophisticated metric designed specifically for code. Think of it like a spell-checker that also understands grammar and context. It compares the model's output to the reference solution by analyzing several components:
    - n-gram match (like BLEU): Checks for overlapping sequences of tokens (words/code elements).

    - Syntactic AST Match: Compares the Abstract Syntax Tree (AST) of the generated code and the reference. This verifies if the code has the same underlying structure and logic.

    - Data-flow Match: Analyzes how variables are read and written to see if the logic flow is the same.

CodeBLEU gives a much better sense of semantic correctness than exact match alone.

# Functional Correctness Testing ✅

This is the most crucial step. A fix is useless if it breaks the program or doesn't actually solve the vulnerability. You'll need to create an automated pipeline that does the following for each generated fix:

1. Syntax & Linter Check: First, check if the generated code is even valid. Does it compile? Does it pass a basic linter (like pylint for Python or eslint for JavaScript)? If not, it's an immediate failure.

2. Unit Test Pass Rate: If you have unit tests associated with the original vulnerable code, run them against the newly patched code. The fix should not break existing functionality. A successful fix is one that keeps all relevant unit tests passing.

3. Vulnerability Re-Scan: This closes the loop. After applying the model's generated fix, run the same security tool that found the original problem (e.g., Semgrep) on the patched code. The vulnerability should no longer be detected. This is the ultimate test of whether the "self-healing" was successful.

### Summary of the Scoring Workflow

To get a complete picture of your model's accuracy, you should combine these methods into a final score or dashboard:

| Metric              | Question It Answers                                     | Why It's Important                               |
|---------------------|---------------------------------------------------------|--------------------------------------------------|
| Exact Match         | Did the model produce the exact expected fix?           | Provides a simple, strict baseline.              |
| CodeBLEU            | Is the model's code structurally and logically similar? | Measures the semantic quality of the code fix.   |
| Syntax Check        | Is the generated code valid and compilable?             | Filters out nonsensical or broken suggestions.   |
| Unit Test Pass Rate | Does the fix break existing program functionality?      | Ensures the model's fixes are safe to implement. |
| Vulnerability Scan  | Did the fix actually resolve the security issue?        | Confirms the primary goal of the model is met.   |

By using this comprehensive evaluation strategy, you can be confident that you are accurately measuring your model's ability to perform its "self-healing" task effectively and reliably.

# Automated Scoring Workflow

The scoring process is fully automated. It works by comparing your model's suggested fix against a pre-existing "answer key"—the correct fix you've already collected in your test dataset. You don't apply the fixes yourself; an automated script does it in a temporary environment to score the result.

Here’s a clearer breakdown of the automated workflow.

### The Role of the "Answer Key"

Think of your test set as a final exam for your model. For each question (a piece of vulnerable code), you already have the correct answer written down (the corresponding fixed code). Your model takes the exam, provides its answers (the generated fixes), and your scoring pipeline acts as the teacher, automatically grading the model's answers against your key.

### The Automated Scoring Pipeline

For each item in your test set, your evaluation script will automatically perform these steps:

1. Give the Prompt: The script feeds the vulnerable code from the test set to your tuned model.
2. Generate a Fix: Your model generates a proposed fix.
3. Compare to the "Answer" (Code-Level Scoring):
    - The script first compares the model's proposed fix to the correct fix from your test set.
    - This is where it calculates metrics like Exact Match (is it identical?) and CodeBLEU (is it structurally similar?).
4. Test in a Sandbox (Functional Scoring):
    - The script then takes the original vulnerable code, applies the model's proposed fix to it in a temporary, isolated environment (a "sandbox").
    - It then automatically runs the functional checks on this temporarily patched code:
        - Does it compile or pass a linter?
        - Do the original unit tests still pass?
        - Does a re-run of Semgrep show the vulnerability is gone?

5. Log the Results: The script records the scores and pass/fail results for each test item and then deletes the temporary code. It repeats this for every vulnerability in your test set.

You don't do any of this manually. The entire process is a hands-off, automated pipeline. The "fixing" only happens ephemerally inside this script for the sole purpose of scoring. The heavy lifting for you is in preparing the initial dataset; the evaluation is a script you run to grade your model's performance.

# Public datasets

Using a public Kaggle dataset for scoring is a great way to benchmark your model's performance against a standardized set of data.

Several Kaggle datasets are well-suited for this, providing the exact "vulnerability-and-fix" pairs you need for your automated evaluation pipeline.

### Recommended Kaggle Dataset

The most prominent and relevant one is the Vulnerability Fix Dataset.

- What it is: This dataset contains thousands of functions and code snippets sourced from the commit histories of real-world open-source projects. Each entry provides the code before a security patch was applied and the code after it was fixed.

- Why it's perfect for scoring: It gives you a ready-made, high-quality test set. The "vulnerable" code is the prompt you feed to your model, and the "fixed" code is the "answer key" you use to score its output automatically.

### How to Use It in Your Scoring Process

Here’s how you would integrate it into your workflow:

1. Download and Split the Data: Download the dataset from Kaggle. The best practice is to partition this data into three separate sets:
    - Training Set (70-80%): Use this to fine-tune your OLMo model.
    - Validation Set (10-15%): Use this to check your model's progress during training and adjust parameters.
    - Test Set (10-15%): Keep this set completely separate. The model should never see this data until the final scoring phase.

2. Train Your Model: Fine-tune your OLMo model using only the training and validation sets.

3. Score Against the Test Set: Once training is complete, run your automated scoring pipeline on the test set. Your script will:
    - Feed the vulnerable code from the test set to your model.
    - Compare the model's generated fix against the ground-truth fix in the test set to calculate metrics like CodeBLEU and Exact Match.
    - Run functional tests to confirm the generated fix works and actually resolves the vulnerability.

Using a public dataset like this is a fantastic approach. It ensures your model's score is objective, reproducible, and not biased toward the specific types of vulnerabilities found only in your own projects.

# Where does webauthn project data fit

Your project-specific data from Trivy and ZAP is highly valuable and should be used for a second, more specialized phase of fine-tuning.

Think of it as a two-stage training process:

1. General Education (Kaggle Dataset): First, you train your model on the large, diverse Kaggle dataset. This gives it a broad, foundational understanding of how to fix a wide variety of common code vulnerabilities. This is like its "bachelor's degree" in code repair.

2. Specialized Training (Your Project Data): After the general training, you perform a second round of fine-tuning using the data from your Trivy and ZAP scans. This makes the model an expert on the specific types of vulnerabilities and dependencies that are common in your own environment. This is its "on-the-job training."

### How to Use Your Trivy and ZAP Data

Your process would look like this:

1. Parse the Reports: Create scripts to parse the JSON or XML output from Trivy and ZAP scans of your projects.

2. Create Instruction Pairs: Convert the parsed data into the same instruction format you used for the Kaggle dataset.
    - For Trivy: The input would be the vulnerable library and version, and the output would be the instruction to upgrade to the fixed version.

```json

{
  "instruction": "Resolve the dependency vulnerability.",
  "input": "Project uses vulnerable library `log4j` version `2.14.1`.",
  "output": "Upgrade `log4j` to version `2.17.1` or higher."
}
```

For ZAP: The input would be the description of the vulnerability (e.g., "Missing Content Security Policy header"), and the output would be the recommended remediation from the report.

```json
{
  "instruction": "Fix the web configuration vulnerability.",
  "input": "The web server is missing a Content Security Policy (CSP) header.",
  "output": "Add a Content Security Policy header to the HTTP response to restrict the sources of content."
}
```

3. Conduct Secondary Fine-Tuning: Take the model you already fine-tuned on the Kaggle data and continue its training using this smaller, highly specific dataset from your own projects.

By following this two-stage approach, you create a model that is not only generally competent at fixing code but is also exceptionally good at fixing the issues that matter most to you and your projects.
