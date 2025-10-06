# RAG Optimization: Systematic Testing Plan for OLMo-2-1B

## Executive Summary

This document outlines a systematic approach to optimize the security vulnerability analysis quality for the OLMo-2-1B model used in Phase 2 of the security analysis pipeline (see `gemini-refactor-plan.md`).

**Current State**: The pipeline generates three different analysis fields for each vulnerability:
1. `raw_analysis` - Unstructured model output
2. `baseline_analysis` - Structured parsing (impact/remediation/prevention)
3. `enhanced_analysis` - RAG-enhanced with historical context

Current RAG shows marginal improvement (0.3 points on 0-100 scale) with high variability and quality issues including repetition loops, `<|endoftext|>` token leakage, and occasional hallucinations.

**Goal**: Systematically test multiple variable permutations across **all three fields** to:
1. Identify optimal generation parameters
2. Determine which field provides consistently highest quality
3. Make evidence-based decision for Phase 3 dataset construction

**Key Insight**: User observation indicates `raw_analysis` field may be higher quality than the other two fields, but this needs systematic validation across all parameter configurations and vulnerability types.

**Critical Question**: Which of the three fields should we use in production for Phase 3 dataset construction?

---

## 1. Background and Context

### 1.1 The Gemini Refactor Plan

The current refactoring initiative (documented in `gemini-refactor-plan.md`) aims to consolidate the 8+ phase security analysis pipeline into a cleaner 5-phase architecture:

1. **Phase 1: Parse & Categorize** - Ingest and categorize security scan reports
2. **Phase 2: Analyze & Narrate** - **RAG-enhanced AI analysis of vulnerabilities** ⬅️ **THIS IS WHERE RAG OPTIMIZATION APPLIES**
3. **Phase 3: Construct Datasets** - Aggregate training data from multiple sources
4. **Phase 4: Train Model** - Fine-tune with quality-weighted sampling
5. **Phase 5: Upload Artifacts** - Publish to Hugging Face Hub

**Phase 2 is the critical focus** for RAG optimization because it directly impacts:
- Quality of AI-generated vulnerability analyses
- Quality of narratives used in training data construction (Phase 3)
- Overall model performance after fine-tuning (Phase 4)

### 1.2 Current RAG Implementation

**File**: `security-ai-analysis/rag_enhanced_olmo_analyzer.py`

**Architecture**:
- Base model: OLMo-2-1B (1 billion parameters, Apple MLX-optimized)
- Knowledge base: FAISS vector index with 340 historical vulnerability embeddings
- Similarity search: sentence-transformers `all-MiniLM-L6-v2`
- Context enhancement: Top 3 similar historical cases added to prompt

**Current Parameters** (as of October 2025):
```python
# Baseline (olmo_analyzer.py)
max_tokens = 150
repetition_penalty = 1.1
temperature = 0.3
top_p = 0.9
top_k = 0

# RAG-enhanced (rag_enhanced_olmo_analyzer.py)
max_tokens = 200           # 33% more than baseline
repetition_penalty = 1.2   # 9% stronger than baseline
temperature = 0.3          # Same as baseline
top_p = 0.9               # Same as baseline
top_k = 0                 # Same as baseline
```

### 1.3 RAG Optimization Research

The implementation incorporates findings from three research sources (see `rag_enhanced_olmo_analyzer.py` lines 167-185):

#### Research Source 1: RAG Capabilities of Small Models (Phi-3 3.8B)
**URL**: https://medium.com/data-science-at-microsoft/evaluating-rag-capabilities-of-small-language-models-e7531b3a5061

**Key Findings**:
- Context window limits (~864 tokens for effective processing)
- Performance degrades significantly with complex prompts
- Small models struggle to synthesize information from multiple sources
- Recommended: Keep context concise, prioritize most relevant information

**Applied Principles**:
- Limited similar cases to top 3 (not 5+)
- Compressed similar case format (60 chars vs 100 chars per case)
- Total prompt size kept under 500 tokens

#### Research Source 2: RAG Prompt Templates and Contextual Understanding
**URL**: https://medium.com/@ajayverma23/the-art-and-science-of-rag-mastering-prompt-templates-and-contextual-understanding-a47961a57e27

**Key Findings**:
- Simple, direct prompts > complex multi-step instructions for SLMs (Small Language Models)
- Avoid meta-instructions like "Based on the following context..."
- Direct task specification improves response quality
- Meta-cognitive instructions ("think step by step") less effective on small models

**Applied Principles**:
- Removed "Based on similar cases..." meta-instruction
- Matched baseline prompt structure EXACTLY
- Moved similar cases to passive context position
- Eliminated multi-step reasoning instructions

#### Research Source 3: OLMo-2 Best Practices
**URL**: https://www.promptingguide.ai/models/olmo

**Key Findings**:
- Direct task specification works best
- Concise context preferred over verbose explanations
- Avoid excessive few-shot examples (1-2 max, or zero-shot)
- Model performs better with focused, single-task prompts

**Applied Principles**:
- Zero-shot prompt (no few-shot examples)
- Concise task instruction: "Provide a concise security analysis with:"
- Removed baseline analysis from prompt (avoid prompt bloat)
- Kept vulnerability context minimal and structured

### 1.4 Experimental History

**Token Limit Experiments**:
| max_tokens | Result | Issues Observed |
|-----------|--------|-----------------|
| 150 | Baseline quality | Mid-sentence cutoffs, incomplete thoughts |
| 200 | Current RAG setting | Moderate quality, some repetition |
| 250 | Tested | 50/50 split with baseline, marginal 0.3 improvement |
| 350 | Tested and reverted | Severe hallucinations, `<|endoftext|>` leakage, unrelated content |

**Key Findings**:
- 150 tokens: Too restrictive, causes cutoffs
- 200-250 tokens: Optimal range for 1B model
- 350+ tokens: Exceeds model's reliable generation capacity
- Repetition penalty 1.1-1.2: Effective range (>1.3 causes quality degradation)

**Quality Issues Persist Across Settings**:
- 70-80% of cases show 25-45% sentence repetition
- `<|endoftext|>` token leakage in ~5-10% of cases
- Occasional unrelated content ("Why do we need proxy in web development?")
- Wrong CVE references in enhanced analysis
- Model hallucinating training data when confused

---

## 2. Critical User Observation

**Quote**: "I also notice at times the raw_analysis field seemed more relevant than the others"

**Critical Context**: The current pipeline generates **three different analysis fields** for each vulnerability, and we need to systematically determine which one provides the highest quality for use in Phase 3 dataset construction.

### 2.1 Field Definitions

**Three Analysis Fields in Output** (all three must be evaluated):

1. **`raw_analysis`**: Unstructured model output, direct generation response
   ```json
   "raw_analysis": "CVE-2024-47554 is a vulnerability in the Commons IO library. This vulnerability allows an attacker to execute arbitrary code... Remediation: The vulnerability can be mitigated by using a different library or by upgrading to a newer version..."
   ```

2. **`baseline_analysis`**: Structured extraction from raw_analysis
   ```json
   "baseline_analysis": {
     "impact": "Security impact requires further investigation",
     "remediation": "The vulnerability can be mitigated by using a different library or by upgrading to a newer version...",
     "prevention": "Implement security monitoring and regular updates"
   }
   ```

3. **`enhanced_analysis`**: RAG-enhanced generation with historical context
   ```json
   "enhanced_analysis": "This vulnerability is a memory corruption issue in the Netty framework. The vulnerability is triggered by an incorrect access to a buffer, which can lead to the execution of arbitrary code..."
   ```

### 2.2 Quality Comparison from Sample Data

**Example: CVE-2024-47554 (Commons IO RCE)**
- ✅ **raw_analysis**: Correct vulnerability (Commons IO), coherent explanation, proper remediation
- ⚠️ **baseline_analysis**: Mid-sentence cutoff, generic prevention text
- ❌ **enhanced_analysis**: Wrong vulnerability (Netty instead of Commons IO), mixed CVE listings, incomplete

**Example: GHSA-5jpm-x58v-624v (Denial of Service)**
- ✅ **raw_analysis**: Coherent analysis, specific remediation (fcntl/ioctl functions)
- ⚠️ **baseline_analysis**: Extracted specific remediation, generic prevention
- ❌ **enhanced_analysis**: Cuts off mid-sentence with `<|endoftext|>`, contains math problem hallucination

**Example: 90004 (ZAP - Cross-Origin-Resource-Policy)**
- ❌ **raw_analysis**: Severe repetition loop, mid-sentence cutoff
- ❌ **baseline_analysis**: Generic placeholders
- ❌ **enhanced_analysis**: Fragmented HTML, excessive repetition

### 2.3 Three-Way Comparison Hypothesis

**Current Uncertainty**: We don't know which of the three fields is consistently highest quality across different vulnerability types and parameter settings.

**Potential Outcomes**:
1. **`raw_analysis` wins**: Unstructured output is most coherent → Use raw directly in Phase 3
2. **`baseline_analysis` wins**: Structured parsing preserves quality → Keep current pipeline approach
3. **`enhanced_analysis` wins**: RAG provides value → Validate RAG optimization success
4. **Tie/Context-dependent**: Different fields win for different vulnerability types → Implement routing logic

**Testing Requirement**: Every parameter configuration must score **all three fields** independently to determine the consistent winner across the quality landscape.

---

## 3. Variables Available for Optimization

### 3.1 MLX Generation Parameters

**Location**: `olmo_analyzer.py` lines 169-287, specifically `_generate_with_prompt()` method

**Tunable Parameters**:

1. **`max_tokens`** (currently 150 baseline, 200 RAG)
   - **Type**: Integer
   - **Range**: 100-300 (beyond 300 shows severe quality degradation)
   - **Impact**: Controls response length, affects completeness and hallucination risk
   - **Trade-off**: More tokens = complete thoughts but higher hallucination risk

2. **`repetition_penalty`** (currently 1.1 baseline, 1.2 RAG)
   - **Type**: Float
   - **Range**: 1.0-1.3 (>1.3 causes quality degradation per research)
   - **Impact**: Reduces repetitive sentence loops
   - **Trade-off**: Higher penalty = less repetition but potential coherence loss

3. **`temperature`** (currently 0.3 for both)
   - **Type**: Float
   - **Range**: 0.1-1.0
   - **Impact**: Controls randomness/creativity in generation
   - **Current**: 0.3 (focused, deterministic output)
   - **Trade-off**: Lower = more focused but potentially repetitive, Higher = more diverse but less reliable

4. **`top_p`** (nucleus sampling, currently 0.9 for both)
   - **Type**: Float
   - **Range**: 0.5-1.0
   - **Impact**: Cumulative probability threshold for token selection
   - **Current**: 0.9 (sample from top 90% probability mass)
   - **Trade-off**: Lower = more focused/conservative, Higher = more diverse

5. **`top_k`** (currently 0 = disabled for both)
   - **Type**: Integer
   - **Range**: 0 (disabled), 10-100
   - **Impact**: Limits selection to top K tokens
   - **Current**: Disabled (relies on top_p instead)
   - **Trade-off**: Enabled = more controlled output, Disabled = broader vocabulary

6. **`repetition_context_size`** (currently 20 for both)
   - **Type**: Integer
   - **Range**: 10-50
   - **Impact**: Number of previous tokens considered for repetition penalty
   - **Current**: 20 tokens lookback
   - **Trade-off**: Larger = broader repetition detection, smaller = more local control

### 3.2 RAG-Specific Parameters

**Location**: `rag_enhanced_olmo_analyzer.py`

7. **Number of similar cases** (currently 3)
   - **Type**: Integer
   - **Range**: 1-5
   - **Impact**: Amount of historical context provided
   - **Trade-off**: More cases = richer context but higher prompt token count

8. **Similar case format verbosity** (currently compressed: 60 chars)
   - **Type**: String format template
   - **Impact**: Prompt token consumption
   - **Trade-off**: Verbose = more context but token overhead, Compressed = efficient but less detail

9. **Similarity threshold** (currently no threshold, top-k only)
   - **Type**: Float
   - **Range**: 0.5-1.0
   - **Impact**: Minimum similarity score to include a case
   - **Trade-off**: Higher threshold = only highly relevant cases but potentially fewer examples

### 3.3 Prompt Structure Variables

10. **Include baseline analysis in prompt** (currently excluded)
    - **Type**: Boolean
    - **Impact**: Provides baseline as reference but increases prompt size
    - **Trade-off**: Context vs token budget

11. **Prompt instruction format** (currently: numbered list)
    - **Type**: String template
    - **Options**: Numbered list, paragraph, bullet points
    - **Impact**: Clarity of task specification

---

## 4. Systematic Testing Plan

### 4.1 Testing Infrastructure Requirements

**New Script**: `scripts/rag_parameter_grid_search.py`

**Core Functions**:

1. **`run_single_configuration()`**
   - Executes RAG analysis with specific parameter set
   - Saves results to `results/rag_experiments/{config_id}/`
   - Returns performance metrics

2. **`calculate_quality_scores()`**
   - Scores all three fields: `raw_analysis`, `baseline_analysis`, `enhanced_analysis`
   - Quality heuristics (0-100 scale):
     - `<|endoftext|>` token presence: -50 points
     - Unrelated content detection: -40 points
     - High repetition ratio (>30%): -20 to -40 points
     - Generic placeholders ("requires further investigation"): -15 points
     - Wrong CVE references: -30 points
     - Mid-sentence cutoffs: -20 points
     - Specificity bonus (CVE references, versions, code snippets): +10 points
   - Returns scores for each field

3. **`compare_against_baseline()`**
   - Loads baseline results (current 150 token, 1.1 repetition_penalty)
   - Compares win/loss/tie for each field
   - Statistical significance testing (paired t-test)
   - Returns comparative metrics

4. **`generate_experiment_report()`**
   - Creates markdown report with:
     - Configuration summary table
     - Quality score distributions
     - Best performing configurations
     - Statistical analysis
     - Sample comparisons (best vs worst cases)

### 4.2 Testing Strategy: Phased Approach

**Phase 1: Core Parameter Sweep (Baseline Optimization)**
- **Goal**: Find optimal `max_tokens` and `repetition_penalty` for baseline model
- **Variables**:
  - `max_tokens`: [150, 175, 200, 225, 250]
  - `repetition_penalty`: [1.0, 1.1, 1.2, 1.3]
- **Fixed**: temperature=0.3, top_p=0.9, top_k=0
- **Configurations**: 5 × 4 = 20 configurations
- **Output Fields Evaluated**: **All three** (`raw_analysis`, `baseline_analysis`, `enhanced_analysis`)
- **Success Metric**: Configuration that maximizes average quality across all three fields

**Phase 2: Sampling Parameter Tuning**
- **Goal**: Test temperature and nucleus sampling impact
- **Start From**: Best Phase 1 configuration
- **Variables**:
  - `temperature`: [0.1, 0.2, 0.3, 0.4, 0.5]
  - `top_p`: [0.7, 0.8, 0.9, 0.95]
- **Configurations**: 5 × 4 = 20 configurations
- **Output Fields Evaluated**: **All three** (`raw_analysis`, `baseline_analysis`, `enhanced_analysis`)
- **Success Metric**: Improved average quality without increased hallucination across all fields

**Phase 3: RAG Context Optimization**
- **Goal**: Optimize RAG-specific parameters
- **Start From**: Best Phase 2 configuration
- **Variables**:
  - `num_similar_cases`: [1, 2, 3, 4, 5]
  - `similarity_threshold`: [None, 0.6, 0.7, 0.8]
  - `include_baseline_in_prompt`: [True, False]
- **Configurations**: 5 × 4 × 2 = 40 configurations
- **Output Fields Evaluated**: **All three** (with focus on whether `enhanced_analysis` improves over `raw_analysis` and `baseline_analysis`)
- **Success Metric**: `enhanced_analysis` quality consistently beats both `raw_analysis` and `baseline_analysis`

**Phase 4: Three-Way Field Comparison & Final Decision**
- **Goal**: Definitively determine which output field to use in production
- **Start From**: Best Phase 3 configuration
- **Analysis**:
  - Run comprehensive scoring on all three fields across all 59 vulnerabilities
  - Calculate win/loss/tie for each pairwise comparison (raw vs baseline, raw vs enhanced, baseline vs enhanced)
  - Statistical significance testing (paired t-test, Wilcoxon signed-rank test)
  - Vulnerability-type stratification (does winner vary by tool/severity?)
  - Identify consistent winner or context-dependent routing strategy
- **Decision Matrix**:
  - `raw_analysis` wins → Use raw, disable parsing/RAG overhead
  - `baseline_analysis` wins → Keep structured parsing, disable RAG
  - `enhanced_analysis` wins → RAG provides value, use enhanced
  - Context-dependent → Implement routing logic based on vulnerability characteristics

### 4.3 Experiment Configuration Format

**Example Configuration File**: `results/rag_experiments/config_001.json`
```json
{
  "experiment_id": "config_001",
  "phase": "Phase 1: Core Parameter Sweep",
  "timestamp": "2025-10-05T14:30:00",
  "parameters": {
    "max_tokens": 200,
    "repetition_penalty": 1.2,
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 0,
    "repetition_context_size": 20,
    "num_similar_cases": 3,
    "similarity_threshold": null,
    "include_baseline_in_prompt": false,
    "prompt_format": "numbered_list"
  },
  "model": {
    "name": "OLMo-2-1B-1124-Instruct",
    "path": "/Users/vinayakmenon/shared-olmo-models/base/OLMo-2-1B-1124-Instruct-Q8_0-mlx",
    "mlx_optimized": true
  },
  "knowledge_base": {
    "size": 340,
    "embedding_model": "all-MiniLM-L6-v2"
  }
}
```

### 4.4 Quality Scoring Implementation

**Script**: `scripts/quality_scorer.py`

```python
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

class QualityScorer:
    """Score vulnerability analysis quality on 0-100 scale."""

    def __init__(self):
        self.generic_phrases = [
            "requires further investigation",
            "security impact",
            "implement security monitoring",
            "regular updates",
            "best practices"
        ]

        self.unrelated_keywords = [
            "web development",
            "proxy server",
            "bash script",
            "I am trying to",
            "how do I",
            "what is the value"
        ]

    def score_analysis(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a single analysis text.

        Args:
            text: The analysis text to score
            context: Vulnerability context (id, tool, severity)

        Returns:
            Dict with score and issue breakdown
        """
        score = 100  # Start at perfect score
        issues = []

        # Critical issues
        if '<|endoftext|>' in text:
            score -= 50
            issues.append("endoftext_token_leakage")

        # Unrelated content detection
        unrelated_count = sum(1 for keyword in self.unrelated_keywords if keyword.lower() in text.lower())
        if unrelated_count > 0:
            score -= 40
            issues.append(f"unrelated_content_{unrelated_count}_keywords")

        # Repetition analysis
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if len(sentences) > 1:
            unique_sentences = set(sentences)
            repetition_ratio = 1 - (len(unique_sentences) / len(sentences))

            if repetition_ratio > 0.3:  # >30% repetition
                penalty = int(repetition_ratio * 100)
                score -= min(penalty, 40)
                issues.append(f"high_repetition_{int(repetition_ratio*100)}%")

        # Generic content detection
        generic_count = sum(1 for phrase in self.generic_phrases if phrase.lower() in text.lower())
        if generic_count > 2:
            score -= 15
            issues.append(f"generic_content_{generic_count}_phrases")

        # Wrong CVE reference detection
        vuln_id = context.get('id', '')
        if vuln_id.startswith('CVE-'):
            # Find all CVE references in text
            cve_refs = re.findall(r'CVE-\d{4}-\d{4,}', text)
            if cve_refs and vuln_id not in cve_refs:
                score -= 30
                issues.append(f"wrong_cve_reference_{cve_refs[0]}")

        # Mid-sentence cutoff detection
        if text and not text.rstrip().endswith(('.', '!', '?', '"', "'")):
            score -= 20
            issues.append("mid_sentence_cutoff")

        # Specificity bonus
        has_version = bool(re.search(r'\d+\.\d+\.\d+', text))
        has_code = 'code' in text.lower() or '```' in text
        has_specific_remediation = any(term in text.lower() for term in ['upgrade', 'patch', 'update', 'fix', 'sanitize', 'validate'])

        specificity_bonus = 0
        if has_version:
            specificity_bonus += 3
        if has_code:
            specificity_bonus += 3
        if has_specific_remediation:
            specificity_bonus += 4

        score += specificity_bonus
        if specificity_bonus > 0:
            issues.append(f"specificity_bonus_{specificity_bonus}")

        # Clamp score to 0-100
        score = max(0, min(100, score))

        return {
            'score': score,
            'issues': issues,
            'text_length': len(text),
            'sentence_count': len(sentences)
        }

    def score_all_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Score all three analysis fields in a result."""
        context = {
            'id': result.get('vulnerability_id'),
            'tool': result.get('tool'),
            'severity': result.get('severity')
        }

        scores = {}

        # Score raw_analysis
        if 'raw_analysis' in result:
            scores['raw_analysis'] = self.score_analysis(result['raw_analysis'], context)

        # Score baseline_analysis (concatenate fields)
        if 'baseline_analysis' in result:
            baseline = result['baseline_analysis']
            baseline_text = f"{baseline.get('impact', '')} {baseline.get('remediation', '')} {baseline.get('prevention', '')}"
            scores['baseline_analysis'] = self.score_analysis(baseline_text, context)

        # Score enhanced_analysis
        if 'enhanced_analysis' in result:
            scores['enhanced_analysis'] = self.score_analysis(result['enhanced_analysis'], context)

        return scores
```

### 4.5 Experiment Execution Workflow

**Command**: `python scripts/rag_parameter_grid_search.py --phase 1 --parallel 4`

**Workflow**:
```
1. Load Phase 1 configuration matrix (20 configs)
2. For each configuration:
   a. Set parameters in OLMoAnalyzer
   b. Run analysis on all 59 vulnerabilities (or sample subset)
   c. Save results to results/rag_experiments/{config_id}/
   d. Calculate quality scores for all three fields
   e. Store metrics in results/rag_experiments/{config_id}/metrics.json
3. Generate comparative report
4. Identify top 3 configurations
5. Recommend Phase 2 starting configuration
```

**Parallelization**:
- Use multiprocessing to run 4 configurations simultaneously
- Each process gets its own model instance
- Estimated time: ~2-3 hours for Phase 1 (20 configs × 59 vulnerabilities)

### 4.6 Report Format

**Example**: `results/rag_experiments/phase_1_report.md`

```markdown
# Phase 1: Core Parameter Sweep Results

**Execution Date**: 2025-10-05
**Total Configurations**: 20
**Vulnerabilities Analyzed**: 59 per configuration
**Total Analyses**: 1,180

## Top 3 Configurations

### 🥇 Config #12: max_tokens=225, repetition_penalty=1.2

**Average Scores**:
- raw_analysis: 91.3 ± 7.2
- baseline_analysis: 78.5 ± 12.1
- enhanced_analysis: 89.7 ± 9.3

**Win Rate vs Baseline** (baseline = 150 tokens, 1.1 penalty):
- raw_analysis: 78% wins, 15% ties, 7% losses
- enhanced_analysis: 72% wins, 18% ties, 10% losses

**Common Issues**:
- mid_sentence_cutoff: 5% of cases
- high_repetition: 12% of cases
- endoftext_token: 2% of cases

**Statistical Significance**: p < 0.001 (paired t-test vs baseline)

**Sample Best Case** (CVE-2024-47554):
```
raw_analysis (score: 98):
CVE-2024-47554 is a remote code execution vulnerability in Apache Commons IO 2.11.0.
The vulnerability allows attackers to execute arbitrary code by exploiting improper
input validation in file processing operations. Remediation requires upgrading to
version 2.14.0 or higher, which includes input sanitization and bounds checking
improvements. This is a critical security issue that should be addressed immediately.
```

---

### 🥈 Config #15: max_tokens=250, repetition_penalty=1.1

[Similar detailed breakdown...]

---

### 🥉 Config #8: max_tokens=200, repetition_penalty=1.2

[Similar detailed breakdown...]

## Statistical Summary

| Metric | Best (Config #12) | Median | Worst (Config #3) |
|--------|-------------------|--------|-------------------|
| Avg raw_analysis score | 91.3 | 84.7 | 76.2 |
| Avg enhanced_analysis score | 89.7 | 83.1 | 74.8 |
| endoftext_token rate | 2% | 6% | 15% |
| high_repetition rate | 12% | 28% | 45% |

## Recommendations

1. **Proceed to Phase 2** with Config #12 as baseline (225 tokens, 1.2 penalty)
2. **Secondary candidate**: Config #15 (250 tokens, 1.1 penalty) for comparison
3. **Key insight**: Increased tokens (225-250) significantly reduces cutoffs without increasing hallucination when paired with appropriate repetition_penalty

## Three-Way Field Quality Comparison

**Results Summary**:
| Field | Avg Score | Win Rate vs Others | Rank |
|-------|-----------|-------------------|------|
| raw_analysis | 91.3 ± 7.2 | 78% | 🥇 1st |
| enhanced_analysis | 89.7 ± 9.3 | 45% | 🥈 2nd |
| baseline_analysis | 78.5 ± 12.1 | 12% | 🥉 3rd |

**Pairwise Comparisons** (Config #12):
- raw_analysis vs baseline_analysis: raw wins 82%, ties 10%, baseline wins 8%
- raw_analysis vs enhanced_analysis: raw wins 55%, ties 30%, enhanced wins 15%
- enhanced_analysis vs baseline_analysis: enhanced wins 70%, ties 15%, baseline wins 15%

**Implication**: `raw_analysis` shows highest quality and consistency. Consider using raw directly in Phase 3 dataset construction unless Phase 3 RAG optimization significantly improves `enhanced_analysis` performance.
```

---

## 5. Decision Framework

### 5.1 Success Criteria for Each Phase

**Phase 1 Success**:
- At least one configuration achieves average score > 90 for **at least one field**
- Clear ranking established among the three fields
- `<|endoftext|>` token leakage < 5%
- High repetition rate < 15%

**Phase 2 Success**:
- Improved average score over Phase 1 best by ≥2 points across **all three fields**
- Maintained or improved field ranking consistency
- Maintained low error rates
- Statistical significance p < 0.05

**Phase 3 Success**:
- `enhanced_analysis` score beats **both** `raw_analysis` and `baseline_analysis` in ≥60% of cases
- Consistent quality (standard deviation < 10 points) for enhanced field
- RAG provides measurable value over both unstructured raw and structured baseline

**Phase 4 Decision** (Three-way comparison):
- If `raw_analysis` wins consistently → Use raw, disable parsing/RAG, simplify pipeline
- If `baseline_analysis` wins consistently → Keep structured parsing, disable RAG
- If `enhanced_analysis` wins consistently → RAG provides value, use enhanced
- If context-dependent (different winners for different vulnerability types) → Implement routing logic

### 5.2 Abort Conditions

**Abort Phase 1** if:
- No configuration improves over current baseline after 10 configs for **any** of the three fields
- All configurations show >20% `<|endoftext|>` leakage

**Abort Phase 3** if:
- RAG consistently underperforms **both** `raw_analysis` and `baseline_analysis` across all configs
- `enhanced_analysis` never achieves top rank in any configuration
- Decision: Disable RAG, proceed with winner from Phase 2 (either raw or baseline)

### 5.3 Production Integration

**After Phase 4 completion**:

1. **Update `process_artifacts.py` Phase 2**:
   - Set optimal parameters in `OLMoAnalyzer` initialization
   - Configure which field to use for dataset construction
   - Document configuration in code comments

2. **Update `gemini-refactor-plan.md`**:
   - Add "Phase 2 Optimization Results" section
   - Document final parameter configuration
   - Include performance benchmarks

3. **Create production config file**: `config/rag_optimal_config.json`
   ```json
   {
     "model_generation": {
       "max_tokens": 225,
       "repetition_penalty": 1.2,
       "temperature": 0.3,
       "top_p": 0.9
     },
     "rag_settings": {
       "enabled": true,
       "num_similar_cases": 3,
       "similarity_threshold": 0.7
     },
     "output_field": "raw_analysis",
     "quality_baseline": {
       "avg_score": 91.3,
       "std_dev": 7.2
     }
   }
   ```

---

## 6. Implementation Checklist

### 6.1 Infrastructure Setup

- [ ] Create `scripts/rag_parameter_grid_search.py`
- [ ] Create `scripts/quality_scorer.py`
- [ ] Create `results/rag_experiments/` directory structure
- [ ] Add experiment tracking to `.gitignore` (large result files)
- [ ] Document experiment data retention policy

### 6.2 Phase Execution

- [ ] Phase 1: Core Parameter Sweep (20 configs)
- [ ] Phase 1 Report & Decision
- [ ] Phase 2: Sampling Parameter Tuning (20 configs)
- [ ] Phase 2 Report & Decision
- [ ] Phase 3: RAG Context Optimization (40 configs)
- [ ] Phase 3 Report & Decision
- [ ] Phase 4: Field Comparison Analysis
- [ ] Phase 4 Final Report & Production Decision

### 6.3 Documentation Updates

- [ ] Update `gemini-refactor-plan.md` with Phase 2 optimization results
- [ ] Create `config/rag_optimal_config.json`
- [ ] Update `rag_enhanced_olmo_analyzer.py` with final parameters
- [ ] Add optimization methodology to project documentation
- [ ] Create troubleshooting guide based on experiment findings

### 6.4 Production Integration

- [ ] Update `process_artifacts.py` Phase 2 implementation
- [ ] Configure optimal parameters in production code
- [ ] Add quality monitoring to production pipeline
- [ ] Validate end-to-end pipeline with optimized config
- [ ] Benchmark Phase 3 dataset quality improvement

---

## 7. Expected Outcomes

### 7.1 Best Case Scenario: RAG Optimization Successful

- **Winner**: `enhanced_analysis` consistently beats **both** `raw_analysis` and `baseline_analysis`
- **Quality improvement**: 15-20 point increase over current baseline across all fields
- **Error reduction**: `<|endoftext|>` leakage eliminated, repetition <10%
- **Production decision**: Use `enhanced_analysis` in Phase 3 dataset construction
- **Value**: RAG historical context significantly improves vulnerability analysis quality
- **Impact**: Phase 4 fine-tuned model generates higher quality vulnerability fixes

### 7.2 Moderate Case Scenario: Raw Analysis Wins

- **Winner**: `raw_analysis` consistently beats `baseline_analysis` and `enhanced_analysis`
- **Quality improvement**: 10-15 point increase in raw_analysis quality through parameter optimization
- **Insight**: Unstructured output more coherent than parsing or RAG synthesis for 1B model
- **Production decision**: Use `raw_analysis` directly, disable parsing and RAG overhead
- **Simplification**: Streamline Phase 2 pipeline, remove unnecessary processing steps
- **Recommendation**: Revisit parsing/RAG when larger models (3B-7B) available

### 7.3 Moderate Case Scenario: Baseline Analysis Wins

- **Winner**: `baseline_analysis` (structured parsing) beats `raw_analysis` and `enhanced_analysis`
- **Quality improvement**: Parsing logic successfully extracts highest quality content from raw output
- **Insight**: Structured fields (impact/remediation/prevention) preserve quality better than unstructured or RAG
- **Production decision**: Use `baseline_analysis`, disable RAG, keep parsing pipeline
- **Action**: Optimize parsing logic further to maximize extraction quality

### 7.4 Worst Case Scenario: No Clear Winner

- **Result**: Context-dependent - different fields win for different vulnerability types/tools
- **Complexity**: No single field consistently highest quality across all cases
- **Decision options**:
  1. Use highest-average field (acceptable performance across all cases)
  2. Implement routing logic based on vulnerability characteristics (tool/severity/type)
  3. Ensemble approach - combine multiple fields for training data diversity
- **Learning**: 1B parameter model quality highly sensitive to input characteristics
- **Path forward**: Invest in larger models or accept routing complexity

### 7.5 Actionable Insights Regardless of Outcome

- **Quantified parameter impact**: Data-driven understanding of each variable's effect on **all three fields**
- **Quality scoring framework**: Reusable methodology for future model evaluations
- **Three-way field comparison data**: Evidence-based decision on which output field to use in production
- **Performance baselines**: Benchmarks for comparing future model upgrades across all analysis types
- **Documentation**: Comprehensive record of optimization methodology and three-field evaluation results
- **Pipeline optimization**: Clear guidance on whether to simplify (raw), maintain (baseline), or enhance (RAG)

---

## 8. Timeline Estimate

**Phase 1**: 2-3 hours execution + 1 hour analysis = **4 hours total**
**Phase 2**: 2-3 hours execution + 1 hour analysis = **4 hours total**
**Phase 3**: 4-5 hours execution + 2 hours analysis = **7 hours total**
**Phase 4**: 1 hour execution + 2 hours final analysis = **3 hours total**
**Documentation & Integration**: **4 hours**

**Total Estimated Time**: **22 hours** (approximately 3 working days with automated execution)

---

## 9. Dependencies and Prerequisites

### 9.1 Software Requirements

- Python 3.9+
- MLX framework (Apple Silicon)
- Existing OLMo-2-1B model artifacts
- FAISS knowledge base (340 embeddings)
- 59 vulnerability analysis results for testing

### 9.2 Hardware Requirements

- Apple Silicon Mac (M1/M2/M3 for MLX optimization)
- Minimum 16GB RAM (32GB recommended for parallel execution)
- ~10GB free disk space for experiment results

### 9.3 Existing Code Dependencies

- `olmo_analyzer.py` - Base analyzer with configurable generation
- `rag_enhanced_olmo_analyzer.py` - RAG implementation
- `local_security_knowledge_base.py` - FAISS knowledge base
- Sample vulnerability data in `results/rag_analysis/`

---

## 10. Related Documentation

- **Gemini Refactor Plan**: `docs/improvements/in-progress/gemini-refactor-plan.md`
- **Training Data Quality Research**: `docs/improvements/in-progress/security-ai-training-data-quality-research.md`
- **RAG Enhanced Analyzer**: `security-ai-analysis/rag_enhanced_olmo_analyzer.py` (lines 167-185 for research links)
- **Base Analyzer**: `security-ai-analysis/olmo_analyzer.py` (lines 169-287 for generation logic)

---

## 11. Contact and Questions

**For implementation questions or results discussion**:
- Review experimental results in `results/rag_experiments/`
- Consult Phase reports for detailed statistical analysis
- Refer to quality scoring breakdown for issue categorization

**Future enhancements**:
- Automated hyperparameter optimization (Bayesian optimization)
- A/B testing framework for production monitoring
- Integration with larger models when available (OLMo-7B, OLMo-13B)
