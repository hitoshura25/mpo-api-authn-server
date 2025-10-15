#!/usr/bin/env python3
"""
Build Security Knowledge Base from Existing Vulnerability Data

This script implements Phase 2 task 3: Generate embeddings from existing vulnerability data.
It loads existing vulnerability analysis results and builds a FAISS-based knowledge base
for RAG-enhanced security analysis.

Usage:
    python3 build_knowledge_base.py [--results-file path/to/results.json]
    
Author: AI Security Enhancement System
Created: 2025-09-16
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
import logging

# Local imports
from local_security_knowledge_base import LocalSecurityKnowledgeBase


def load_vulnerability_results(results_file: Path) -> List[Dict[str, Any]]:
    """Load vulnerability analysis results from JSON file."""
    
    if not results_file.exists():
        raise FileNotFoundError(f"Results file not found: {results_file}")
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError(f"Expected list of results, got {type(data)}")
    
    return data


def find_latest_results_file() -> Path:
    """Find the narrativized analyses results file."""

    results_dir = Path("results")

    if not results_dir.exists():
        raise FileNotFoundError("Results directory not found")

    # Look for narrativized analyses file
    narrativized_file = results_dir / "narrativized_analyses.json"

    if not narrativized_file.exists():
        raise FileNotFoundError(f"Narrativized analyses file not found: {narrativized_file}")

    return narrativized_file


def build_knowledge_base_from_narrativized_file(narrativized_file: Path) -> bool:
    """
    Build knowledge base from a narrativized analyses JSON file.

    This is the core logic extracted from main() for programmatic use.
    Allows the knowledge base to be rebuilt automatically after narrativization.

    Args:
        narrativized_file: Path to narrativized_analyses.json

    Returns:
        bool: True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)

    try:
        # Load narrativized vulnerability data
        logger.info(f"🔍 Loading narrativized analyses from: {narrativized_file}")
        narrativized_data = load_vulnerability_results(narrativized_file)
        logger.info(f"📊 Loaded {len(narrativized_data)} narrativized analyses")

        if len(narrativized_data) == 0:
            logger.warning("⚠️  No vulnerability data found. Cannot build knowledge base.")
            return False

        # Transform to format expected by knowledge base
        vulnerability_results = []
        for entry in narrativized_data:
            vuln = entry.get('vulnerability', {})
            ai_analysis = entry.get('ai_analysis', '')

            # Parse ai_analysis string format: "Impact: X. Remediation: Y. Prevention: Z"
            baseline_analysis = {}
            if ai_analysis:
                parts = ai_analysis.split('. ')
                for part in parts:
                    if part.startswith('Impact: '):
                        baseline_analysis['impact'] = part.replace('Impact: ', '')
                    elif part.startswith('Remediation: '):
                        baseline_analysis['remediation'] = part.replace('Remediation: ', '')
                    elif part.startswith('Prevention: '):
                        baseline_analysis['prevention'] = part.replace('Prevention: ', '')

            vulnerability_results.append({
                'vulnerability': vuln,
                'analysis': {
                    'baseline_analysis': baseline_analysis
                }
            })

        logger.info(f"✅ {len(vulnerability_results)} entries prepared for knowledge base")

        # Initialize knowledge base
        logger.info("🚀 Initializing LocalSecurityKnowledgeBase...")
        kb = LocalSecurityKnowledgeBase()

        # Build knowledge base
        logger.info("🧠 Building knowledge base with embeddings...")
        build_result = kb.build_knowledge_base_from_results(vulnerability_results)

        if build_result:
            logger.info("✅ Knowledge base built successfully!")
            logger.info(f"   Total processed: {build_result.get('total_processed', 0)}")
            logger.info(f"   Successful embeddings: {build_result.get('successful_embeddings', 0)}")
            return True
        else:
            logger.error("❌ Knowledge base build returned no result")
            raise RuntimeError("Knowledge base build failed")

    except Exception as e:
        logger.error(f"❌ Knowledge base build failed: {e}")
        raise

def main():
    """Main function to build the knowledge base."""
    
    parser = argparse.ArgumentParser(description="Build security knowledge base from vulnerability data")
    parser.add_argument(
        "--results-file", 
        type=Path,
        help="Path to vulnerability analysis results JSON file (defaults to most recent)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Determine results file to use
        if args.results_file:
            results_file = args.results_file
        else:
            results_file = find_latest_results_file()

        logger.info(f"📂 Using results file: {results_file}")

        # Build knowledge base using extracted function
        success = build_knowledge_base_from_narrativized_file(results_file)

        if not success:
            print("❌ Knowledge base build failed")
            sys.exit(1)

        # Get knowledge base for statistics display
        kb = LocalSecurityKnowledgeBase()
        if not kb.load_knowledge_base():
            print("❌ Failed to load knowledge base for statistics")
            sys.exit(1)

        stats = kb.get_knowledge_base_stats()

        # Display results
        print("\n🎉 Knowledge Base Built Successfully!")
        print("=" * 50)
        print(f"📊 Total Vectors: {stats['total_vectors']}")
        print(f"📐 Embedding Dimension: {stats['embedding_dimension']}")
        print(f"🤖 Embedding Model: {stats['embedding_model']}")
        print(f"💾 Index File Size: {stats['index_file_size'] / 1024 / 1024:.1f} MB")
        print(f"📋 Metadata File Size: {stats['metadata_file_size'] / 1024:.1f} KB")
        print(f"📁 Storage Directory: {stats['storage_directory']}")

        print("\n🔧 Tool Distribution:")
        for tool, count in list(stats['tool_distribution'].items())[:5]:  # Top 5
            print(f"   {tool}: {count}")

        print("\n⚠️ Severity Distribution:")
        for severity, count in stats['severity_distribution'].items():
            print(f"   {severity}: {count}")
        
        # Test similarity search
        print("\n🧪 Testing similarity search...")
        test_vulnerability = {
            'tool': 'checkov',
            'severity': 'HIGH',
            'type': 'CKV_DOCKER_2',
            'description': 'Dockerfile missing healthcheck instruction'
        }
        
        similar_vulns = kb.find_similar_vulnerabilities(test_vulnerability, top_k=3)
        
        if similar_vulns:
            print(f"🔍 Found {len(similar_vulns)} similar vulnerabilities:")
            for i, sim in enumerate(similar_vulns, 1):
                metadata = sim['metadata']
                print(f"   {i}. {sim['similarity_percentage']} - {metadata['tool']} - {metadata['type']}")
        
        print("\n✅ Knowledge base is ready for RAG-enhanced analysis!")
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: Knowledge base construction failed: {e}")
        logger.error("🔍 Knowledge base construction failure indicates data corruption, dependency issues, or infrastructure problems requiring investigation")
        if args.verbose:
            import traceback
            traceback.print_exc()
        raise RuntimeError(f"Knowledge base construction failed - requires investigation: {e}") from e


if __name__ == "__main__":
    main()