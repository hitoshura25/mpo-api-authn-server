#!/usr/bin/env python3
"""
Multi-Model Security Evaluation Framework
Compare OLMo against other models (when you're ready)
For now, focuses on evaluating OLMo's performance
"""
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import statistics


class SecurityModelEvaluator:
    """Evaluate AI models on security analysis tasks"""
    
    def __init__(self, dataset_path: str):
        """Initialize with evaluation dataset"""
        self.dataset_path = Path(dataset_path)
        self.load_dataset()
        self.results = {
            "metadata": {
                "evaluation_date": datetime.now().isoformat(),
                "dataset_version": self.dataset.get('metadata', {}).get('version', '1.0.0')
            },
            "models_evaluated": [],
            "task_results": [],
            "model_comparisons": {},
            "summary": {}
        }
    
    def load_dataset(self):
        """Load evaluation tasks"""
        # Look for evaluation tasks file
        eval_files = list(self.dataset_path.parent.glob("evaluation_tasks_*.json"))
        if eval_files:
            with open(eval_files[0], 'r') as f:
                data = json.load(f)
                self.dataset = data
                self.tasks = data.get('tasks', [])
        else:
            print("⚠️ No evaluation tasks found. Please run create_security_dataset.py first")
            self.tasks = []
    
    def evaluate_response_quality(self, response: str, task: Dict) -> Dict[str, float]:
        """
        Evaluate the quality of a model's response
        This is a simplified automatic evaluation - in production, you'd want human evaluation too
        """
        scores = {}
        
        # Check for expected elements
        expected = task.get('expected_elements', [])
        found_elements = sum(1 for elem in expected if elem and elem.lower() in response.lower())
        scores['completeness'] = found_elements / len(expected) if expected else 0.0
        
        # Check response length (not too short, not too long)
        response_length = len(response.split())
        if response_length < 10:
            scores['detail_level'] = 0.2
        elif response_length < 50:
            scores['detail_level'] = 0.5
        elif response_length < 200:
            scores['detail_level'] = 1.0
        else:
            scores['detail_level'] = 0.8  # Might be too verbose
        
        # Check for structure (numbered points, sections, etc.)
        has_structure = any(marker in response for marker in ['1.', '2.', '•', '-', '\n\n'])
        scores['structure'] = 1.0 if has_structure else 0.5
        
        # Check for technical terms (simplified check)
        technical_terms = ['vulnerability', 'security', 'risk', 'impact', 'fix', 'patch', 
                          'update', 'permission', 'access', 'exploit', 'mitigation']
        technical_count = sum(1 for term in technical_terms if term in response.lower())
        scores['technical_accuracy'] = min(technical_count / 5, 1.0)  # Expect at least 5 technical terms
        
        # Calculate overall score
        scores['overall'] = statistics.mean(scores.values())
        
        return scores
    
    def evaluate_olmo_baseline(self) -> Dict:
        """
        Evaluate OLMo's existing responses from the dataset
        This uses the responses already generated
        """
        print("📊 Evaluating OLMo baseline performance...")
        
        model_results = {
            "model_name": "allenai/OLMo-1B",
            "model_type": "baseline",
            "task_scores": [],
            "aggregate_scores": {}
        }
        
        task_type_scores = {}
        
        for task in self.tasks:
            # Get OLMo's response from the dataset
            olmo_response = task.get('olmo_response', '')
            
            if not olmo_response:
                continue
            
            # Evaluate response quality
            scores = self.evaluate_response_quality(olmo_response, task)
            
            task_result = {
                "task_id": task['task_id'],
                "task_type": task['task_type'],
                "scores": scores,
                "response_length": len(olmo_response)
            }
            
            model_results['task_scores'].append(task_result)
            
            # Aggregate by task type
            task_type = task['task_type']
            if task_type not in task_type_scores:
                task_type_scores[task_type] = []
            task_type_scores[task_type].append(scores['overall'])
        
        # Calculate aggregate scores
        all_scores = [t['scores']['overall'] for t in model_results['task_scores']]
        
        model_results['aggregate_scores'] = {
            "mean_score": statistics.mean(all_scores) if all_scores else 0,
            "median_score": statistics.median(all_scores) if all_scores else 0,
            "std_dev": statistics.stdev(all_scores) if len(all_scores) > 1 else 0,
            "by_task_type": {
                task_type: {
                    "mean": statistics.mean(scores),
                    "count": len(scores)
                }
                for task_type, scores in task_type_scores.items()
            }
        }
        
        return model_results
    
    def identify_improvement_areas(self, model_results: Dict) -> List[Dict]:
        """Identify specific areas where OLMo needs improvement"""
        improvements = []
        
        # Find low-scoring task types
        task_type_scores = model_results['aggregate_scores'].get('by_task_type', {})
        
        for task_type, scores in task_type_scores.items():
            if scores['mean'] < 0.6:  # Threshold for "needs improvement"
                improvements.append({
                    "area": task_type,
                    "current_score": scores['mean'],
                    "recommendation": f"OLMo scores {scores['mean']:.2f} on {task_type} tasks. "
                                    f"Consider fine-tuning with more {task_type} examples."
                })
        
        # Find consistently missing elements
        missing_elements = {}
        for task_score in model_results['task_scores']:
            if task_score['scores']['completeness'] < 0.5:
                task_id = task_score['task_id']
                task = next((t for t in self.tasks if t['task_id'] == task_id), None)
                if task:
                    for element in task.get('expected_elements', []):
                        if element:
                            missing_elements[element] = missing_elements.get(element, 0) + 1
        
        # Report frequently missing elements
        for element, count in sorted(missing_elements.items(), key=lambda x: x[1], reverse=True)[:5]:
            improvements.append({
                "area": "missing_element",
                "element": element,
                "frequency": count,
                "recommendation": f"OLMo frequently misses '{element}' in responses ({count} times). "
                                f"Training should emphasize including {element}."
            })
        
        return improvements
    
    def generate_report(self, output_dir: str = "data/evaluation_results"):
        """Generate comprehensive evaluation report"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Evaluate OLMo baseline
        olmo_results = self.evaluate_olmo_baseline()
        self.results['models_evaluated'].append(olmo_results)
        
        # Identify improvements
        improvements = self.identify_improvement_areas(olmo_results)
        
        # Create summary
        self.results['summary'] = {
            "olmo_performance": {
                "overall_score": olmo_results['aggregate_scores']['mean_score'],
                "strengths": [
                    task_type for task_type, scores in 
                    olmo_results['aggregate_scores']['by_task_type'].items()
                    if scores['mean'] > 0.7
                ],
                "weaknesses": [
                    task_type for task_type, scores in 
                    olmo_results['aggregate_scores']['by_task_type'].items()
                    if scores['mean'] < 0.6
                ]
            },
            "improvement_recommendations": improvements,
            "dataset_coverage": {
                "total_tasks": len(self.tasks),
                "tasks_evaluated": len(olmo_results['task_scores']),
                "coverage_percentage": (len(olmo_results['task_scores']) / len(self.tasks) * 100) 
                                     if self.tasks else 0
            }
        }
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_path / f"olmo_evaluation_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n✅ Evaluation report saved to: {report_path}")
        
        # Generate markdown report for easy reading
        markdown_report = self.generate_markdown_report()
        markdown_path = output_path / f"olmo_evaluation_report_{timestamp}.md"
        
        with open(markdown_path, 'w') as f:
            f.write(markdown_report)
        
        print(f"✅ Markdown report saved to: {markdown_path}")
        
        return report_path
    
    def generate_markdown_report(self) -> str:
        """Generate human-readable markdown report"""
        olmo_results = self.results['models_evaluated'][0] if self.results['models_evaluated'] else {}
        summary = self.results['summary']
        
        report = f"""# OLMo Security Evaluation Report

**Date**: {self.results['metadata']['evaluation_date']}  
**Model**: allenai/OLMo-1B  
**Dataset**: WebAuthn Security Dataset v{self.results['metadata']['dataset_version']}

## Executive Summary

**Overall Performance Score**: {summary['olmo_performance']['overall_score']:.2%}

### Strengths ✅
{chr(10).join('- ' + s.replace('_', ' ').title() for s in summary['olmo_performance']['strengths'])}

### Areas for Improvement 📈
{chr(10).join('- ' + w.replace('_', ' ').title() for w in summary['olmo_performance']['weaknesses'])}

## Detailed Scores by Task Type

"""
        
        if olmo_results:
            for task_type, scores in olmo_results['aggregate_scores']['by_task_type'].items():
                report += f"### {task_type.replace('_', ' ').title()}\n"
                report += f"- **Mean Score**: {scores['mean']:.2%}\n"
                report += f"- **Number of Tasks**: {scores['count']}\n\n"
        
        report += """## Improvement Recommendations

"""
        for i, rec in enumerate(summary['improvement_recommendations'][:5], 1):
            report += f"### {i}. {rec.get('area', 'General').replace('_', ' ').title()}\n"
            report += f"{rec['recommendation']}\n\n"
        
        report += f"""## Dataset Coverage

- **Total Tasks Available**: {summary['dataset_coverage']['total_tasks']}
- **Tasks Evaluated**: {summary['dataset_coverage']['tasks_evaluated']}
- **Coverage**: {summary['dataset_coverage']['coverage_percentage']:.1f}%

## Next Steps

1. **Fine-tune OLMo** on identified weak areas using the training examples
2. **Collect more examples** for task types where OLMo performs poorly
3. **Human evaluation** to validate automatic scoring
4. **Compare with other models** when ready (GPT-4, Claude, Gemini)

## For AI2 Collaboration

This evaluation identifies specific areas where OLMo could benefit from additional training:
"""
        
        # Add specific training recommendations
        weak_areas = summary['olmo_performance']['weaknesses']
        if weak_areas:
            for area in weak_areas:
                report += f"- More {area.replace('_', ' ')} examples needed\n"
        
        report += """
---
*Generated by WebAuthn Security AI Analysis System*
"""
        
        return report
    
    def run_evaluation(self):
        """Run complete evaluation pipeline"""
        print("🔬 Starting OLMo Security Evaluation...")
        print("="*60)
        
        if not self.tasks:
            print("❌ No evaluation tasks found. Please run create_security_dataset.py first")
            return None
        
        print(f"📊 Evaluating {len(self.tasks)} tasks...")
        
        # Generate report
        report_path = self.generate_report()
        
        # Print summary
        print("\n" + "="*60)
        print("📈 Evaluation Summary")
        print("="*60)
        
        summary = self.results['summary']
        print(f"Overall Score: {summary['olmo_performance']['overall_score']:.2%}")
        print(f"\nStrengths: {', '.join(summary['olmo_performance']['strengths'])}")
        print(f"Weaknesses: {', '.join(summary['olmo_performance']['weaknesses'])}")
        
        print(f"\n✅ Full report available at: {report_path}")
        
        return report_path


def main():
    # Use the dataset we just created
    dataset_dir = Path("data/security_dataset")
    
    evaluator = SecurityModelEvaluator(dataset_dir)
    report_path = evaluator.run_evaluation()
    
    if report_path:
        print("\n🎯 Ready for AI2 Collaboration!")
        print("Share the evaluation report and dataset with AI2 to help improve OLMo")


if __name__ == "__main__":
    main()
