#!/usr/bin/env python3
"""
RAG-Enhanced OLMo Security Analyzer

This module implements Phase 2 of the AI Security Enhancement plan:
- RAG-enhanced vulnerability analysis using local knowledge base
- Integration with existing MLX-optimized OLMo analyzer
- Dynamic knowledge retrieval for contextual security analysis
- Fallback to baseline analyzer when RAG is not available

Author: AI Security Enhancement System  
Created: 2025-09-16
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

# Local imports
from olmo_analyzer import OLMoSecurityAnalyzer
from local_security_knowledge_base import LocalSecurityKnowledgeBase

class RAGEnhancedOLMoAnalyzer(OLMoSecurityAnalyzer):
    """
    RAG-enhanced security analyzer that augments vulnerability analysis
    with similar historical cases and proven remediation patterns.
    
    Extends the existing OLMoSecurityAnalyzer with RAG capabilities while
    maintaining full backward compatibility.
    """

    def __init__(self, model_name: Optional[str] = None, enable_rag: bool = True):
        """
        Initialize RAG-enhanced analyzer.
        
        Args:
            model_name: Path to OLMo model (uses configured default if None)
            enable_rag: Whether to enable RAG functionality
        """
        
        # Initialize base analyzer
        super().__init__(model_name)
        
        # RAG configuration
        self.rag_enabled = enable_rag
        self.knowledge_base = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize RAG system if enabled
        if self.rag_enabled:
            try:
                self._initialize_rag_system()
            except Exception as e:
                self.logger.warning(f"⚠️ RAG initialization failed, falling back to baseline: {e}")
                raise
        
        self.logger.info(f"✅ RAG-Enhanced analyzer initialized (RAG enabled: {self.rag_enabled})")

    def _initialize_rag_system(self):
        """Initialize the RAG knowledge base system."""
        
        self.logger.info("🚀 Initializing RAG knowledge base...")
        
        # Initialize knowledge base
        self.knowledge_base = LocalSecurityKnowledgeBase()
        
        # Try to load existing knowledge base
        if not self.knowledge_base.load_knowledge_base():
            self.logger.warning("📂 No existing knowledge base found. RAG will be limited until knowledge base is built.")
            # Keep RAG enabled but with limited functionality
            # Users can build knowledge base using build_knowledge_base.py
            
        else:
            # Get knowledge base statistics
            stats = self.knowledge_base.get_knowledge_base_stats()
            self.logger.info(f"📊 Loaded knowledge base with {stats['total_vectors']} vulnerability patterns")
            
            # Log top security tools for context
            top_tools = list(stats['tool_distribution'].items())[:3]
            self.logger.info(f"🔧 Top tools: {', '.join([f'{tool}({count})' for tool, count in top_tools])}")

    def analyze_vulnerability(self, vulnerability: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze vulnerability with optional RAG enhancement.
        
        Args:
            vulnerability: Vulnerability data from security tools
            
        Returns:
            Enhanced analysis with RAG context when available
        """
        
        if self.rag_enabled and self.knowledge_base and self.knowledge_base.vector_index is not None:
            self.logger.info(f"🔍 Performing RAG-enhanced analysis for vulnerability ID: {vulnerability.get('id', 'unknown')}")
            return self._analyze_with_rag(vulnerability)
        else:
            # Fall back to baseline analysis
            self.logger.info(f"🔄 RAG not available, using baseline analysis for vulnerability ID: {vulnerability.get('id', 'unknown')}")
            return super().analyze_vulnerability(vulnerability)
    
    def _analyze_with_rag(self, vulnerability: Dict[str, Any]) -> Dict[str, Any]:
        """Perform RAG-enhanced vulnerability analysis."""
        
        try:
            # Step 1: Get baseline analysis
            baseline_analysis = super().analyze_vulnerability(vulnerability)
            
            # Step 2: Retrieve similar vulnerabilities from knowledge base
            similar_vulnerabilities = self.knowledge_base.find_similar_vulnerabilities(
                vulnerability, top_k=3
            )
            
            if not similar_vulnerabilities:
                self.logger.info("🔍 No similar vulnerabilities found, using baseline analysis")
                return baseline_analysis
            
            # Step 3: Create RAG-enhanced prompt with similar cases
            rag_enhanced_prompt = self._create_rag_enhanced_prompt(
                vulnerability, similar_vulnerabilities, baseline_analysis
            )
            
            # Step 4: Generate enhanced analysis
            enhanced_analysis = self._generate_rag_enhanced_analysis(
                rag_enhanced_prompt, vulnerability, baseline_analysis
            )
            
            # Step 5: Merge with baseline and add RAG metadata
            final_analysis = self._merge_analyses(
                baseline_analysis, enhanced_analysis, similar_vulnerabilities
            )
            
            self.logger.info(f"✅ RAG-enhanced analysis completed with {len(similar_vulnerabilities)} similar cases")
            return final_analysis
            
        except Exception as e:
            self.logger.error(f"❌ RAG analysis failed: {e}")
            raise
    
    def _create_rag_enhanced_prompt(
        self, 
        vulnerability: Dict[str, Any], 
        similar_vulnerabilities: List[Dict[str, Any]],
        baseline_analysis: Dict[str, Any]
    ) -> str:
        """Create enhanced prompt with RAG context."""
        
        # Format similar vulnerabilities in compressed format (optimized for 1B model)
        # Compress format to save tokens: "- TYPE (SEVERITY): description"
        similar_cases = []
        for sim_vuln in similar_vulnerabilities:
            metadata = sim_vuln['metadata']
            # Truncate description to 60 chars for token efficiency
            desc = metadata.get('description', '')[:60]
            case_summary = f"- {metadata['type']} ({metadata['severity']}): {desc}"
            similar_cases.append(case_summary)

        similar_cases_text = "\n".join(similar_cases)

        # RAG prompt optimized for OLMo-2-1B (1B parameter model)
        #
        # Research sources for small language model (SLM) RAG prompt design:
        # 1. RAG capabilities of small models (Phi-3 3.8B analysis):
        #    https://medium.com/data-science-at-microsoft/evaluating-rag-capabilities-of-small-language-models-e7531b3a5061
        #    Key findings: Context window limits (~864 tokens), performance degrades with complex prompts
        #
        # 2. RAG prompt templates and contextual understanding:
        #    https://medium.com/@ajayverma23/the-art-and-science-of-rag-mastering-prompt-templates-and-contextual-understanding-a47961a57e27
        #    Key findings: Simple, direct prompts > complex multi-step instructions for SLMs
        #
        # 3. OLMo-2 best practices:
        #    https://www.promptingguide.ai/models/olmo
        #    Key findings: Direct task specification, concise context, avoid excessive few-shot examples
        #
        # Design principles applied:
        # - Match baseline prompt structure EXACTLY (no meta-instructions like "Based on...")
        # - Remove baseline analysis from prompt (let model generate fresh, avoid repetition)
        # - Add similar cases as passive context before task instruction
        # - Compress similar case format (60 chars vs 100 chars per case)
        # - Keep task instruction identical to baseline for consistency
        #
        rag_prompt = f"""Vulnerability: {vulnerability.get('id', 'unknown')}
Severity: {vulnerability.get('severity', 'unknown')}
Tool: {vulnerability.get('tool', 'unknown')}
Issue: {vulnerability.get('description', vulnerability.get('message', ''))}

Similar cases:
{similar_cases_text}

Provide a concise security analysis with:
1. Impact explanation
2. Specific remediation steps

Analysis:"""

        return rag_prompt
    
    def _format_baseline_analysis(self, baseline_analysis: Dict[str, Any]) -> str:
        """Format baseline analysis for inclusion in RAG prompt."""

        if 'baseline_analysis' in baseline_analysis:
            baseline = baseline_analysis['baseline_analysis']
            return f"""
Impact: {baseline.get('impact', 'N/A')}
Remediation: {baseline.get('remediation', 'N/A')}
Prevention: {baseline.get('prevention', 'N/A')}"""
        else:
            return baseline_analysis.get('raw_analysis', 'No baseline analysis available')
    
    def _generate_rag_enhanced_analysis(
        self,
        rag_prompt: str,
        vulnerability: Dict[str, Any],
        baseline_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate enhanced analysis using RAG-enhanced prompt."""
        
        # Use the same generation method as the base analyzer but with enhanced prompt
        enhanced_response = self._generate_analysis_text(rag_prompt)
        
        # Parse and structure the enhanced response
        return self._parse_enhanced_analysis(enhanced_response, vulnerability)
    
    def _generate_analysis_text(self, prompt: str) -> str:
        """
        Generate analysis text using the base analyzer's generation method.

        Uses higher token limit and stronger repetition penalty for RAG generation
        to reduce cutoffs and repetition loops.
        """

        # Use higher parameters for RAG generation to address quality issues:
        # - max_tokens=250 (vs baseline 150): Gives model room to complete thoughts, reduces mid-sentence cutoffs
        # - repetition_penalty=1.2 (vs baseline 1.1): Reduces repetition loops while staying under 1.3 quality degradation threshold
        return super()._generate_with_prompt(
            prompt,
            vuln_id="rag-enhanced",
            max_tokens=200,           # 67% more tokens to prevent cutoffs
            repetition_penalty=1.2    # Stronger penalty to reduce loops
        )
    
    def _parse_enhanced_analysis(self, enhanced_text: str, vulnerability: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the RAG-enhanced analysis response into structured format."""
        
        # Enhanced analysis structure
        enhanced_analysis = {
            'rag_enhanced': True,
            'enhanced_analysis': enhanced_text,
            'enhancement_type': 'rag_historical_context',
            'analysis_quality': 'enhanced_with_historical_patterns'
        }
        
        # Try to extract specific sections if they exist
        sections = {
            'historical_patterns': self._extract_section(enhanced_text, 'Historical Patterns', 'Enhanced Impact'),
            'enhanced_impact': self._extract_section(enhanced_text, 'Enhanced Impact', 'Proven Remediation'),
            'proven_remediation': self._extract_section(enhanced_text, 'Proven Remediation', 'Contextual Risk'),
            'contextual_risk': self._extract_section(enhanced_text, 'Contextual Risk', 'Implementation Guidance'),
            'implementation_guidance': self._extract_section(enhanced_text, 'Implementation Guidance', None)
        }
        
        # Add non-empty sections
        for section_name, section_content in sections.items():
            if section_content and section_content.strip():
                enhanced_analysis[section_name] = section_content.strip()
        
        return enhanced_analysis
    
    def _extract_section(self, text: str, start_marker: str, end_marker: Optional[str]) -> str:
        """Extract a section from the enhanced analysis text."""
        
        try:
            start_pos = text.find(start_marker)
            if start_pos == -1:
                return ""
            
            start_pos = text.find(':', start_pos) + 1
            
            if end_marker:
                end_pos = text.find(end_marker, start_pos)
                if end_pos == -1:
                    return text[start_pos:].strip()
                else:
                    return text[start_pos:end_pos].strip()
            else:
                return text[start_pos:].strip()
                
        except Exception as e:
            self.logger.error(f"Failed to extract section: {e}")
            raise
    
    def _merge_analyses(
        self,
        baseline_analysis: Dict[str, Any],
        enhanced_analysis: Dict[str, Any],
        similar_vulnerabilities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge baseline and enhanced analyses with RAG metadata."""

        # Start with baseline analysis (keep unchanged)
        merged_analysis = baseline_analysis.copy()

        # Add RAG enhancements (separate from baseline)
        merged_analysis.update(enhanced_analysis)

        # Add RAG metadata
        merged_analysis['rag_metadata'] = {
            'rag_enhanced': True,
            'similar_cases_count': len(similar_vulnerabilities),
            'similar_cases_summary': [
                {
                    'tool': sim['metadata']['tool'],
                    'type': sim['metadata']['type'],
                    'similarity': sim['similarity_percentage']
                } for sim in similar_vulnerabilities
            ],
            'enhancement_method': 'local_faiss_similarity_search',
            'knowledge_base_size': self.knowledge_base.get_knowledge_base_stats()['total_vectors']
        }

        # NOTE: baseline_analysis is kept unchanged for reliable fallback
        # RAG enhancements are in separate fields: enhanced_analysis, rag_metadata

        return merged_analysis
    
    def get_rag_status(self) -> Dict[str, Any]:
        """Get current RAG system status and statistics."""
        
        if not self.rag_enabled:
            return {
                'status': 'disabled',
                'reason': 'RAG was disabled during initialization'
            }
        
        if not self.knowledge_base:
            return {
                'status': 'not_initialized',
                'reason': 'Knowledge base not initialized'
            }
        
        # Get knowledge base statistics
        kb_stats = self.knowledge_base.get_knowledge_base_stats()
        
        return {
            'status': 'active' if kb_stats['status'] == 'available' else 'limited',
            'knowledge_base': kb_stats,
            'rag_capabilities': {
                'similarity_search': kb_stats['status'] == 'available',
                'historical_context': kb_stats['status'] == 'available',
                'enhanced_remediation': kb_stats['status'] == 'available'
            }
        }


def test_rag_enhanced_analyzer():
    """Test function for RAG-enhanced analyzer."""
    
    print("🧪 Testing RAG-Enhanced OLMo Analyzer...")
    
    try:
        # Initialize RAG-enhanced analyzer
        analyzer = RAGEnhancedOLMoAnalyzer(enable_rag=True)
        
        # Get RAG status
        rag_status = analyzer.get_rag_status()
        print(f"📊 RAG Status: {rag_status['status']}")
        
        if rag_status['status'] in ['active', 'limited']:
            kb_stats = rag_status['knowledge_base']
            print(f"🗃️ Knowledge base: {kb_stats['total_vectors']} vectors")
            
            # Test with sample vulnerability
            test_vulnerability = {
                'tool': 'checkov',
                'severity': 'HIGH',
                'id': 'CKV_DOCKER_2',
                'type': 'CKV_DOCKER_2',
                'description': 'Dockerfile missing healthcheck instruction for container monitoring',
                'file_path': 'path/to/Dockerfile',
                'message': 'Healthcheck missing in Docker container configuration'
            }
            
            print("🔍 Testing RAG-enhanced analysis...")
            
            # Note: This would require the model to be loaded, which takes time
            # For testing purposes, we'll just verify the RAG system is working
            if analyzer.knowledge_base and analyzer.knowledge_base.vector_index:
                similar = analyzer.knowledge_base.find_similar_vulnerabilities(
                    test_vulnerability, top_k=3
                )
                print(f"✅ Found {len(similar)} similar vulnerabilities for test case")
                
                for i, sim in enumerate(similar, 1):
                    metadata = sim['metadata']
                    print(f"   {i}. {sim['similarity_percentage']} - {metadata['tool']} - {metadata['type']}")
            
        print("✅ RAG-enhanced analyzer test completed successfully")
        
    except Exception as e:
        print(f"❌ RAG-enhanced analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    test_rag_enhanced_analyzer()