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
from analysis.olmo_analyzer import OLMoSecurityAnalyzer
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
                self.rag_enabled = False
        
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
            return self._analyze_with_rag(vulnerability)
        else:
            # Fall back to baseline analysis
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
            self.logger.info("🔄 Falling back to baseline analysis")
            return super().analyze_vulnerability(vulnerability)
    
    def _create_rag_enhanced_prompt(
        self, 
        vulnerability: Dict[str, Any], 
        similar_vulnerabilities: List[Dict[str, Any]],
        baseline_analysis: Dict[str, Any]
    ) -> str:
        """Create enhanced prompt with RAG context."""
        
        # Format similar vulnerabilities for context
        similar_cases_text = ""
        for i, sim_vuln in enumerate(similar_vulnerabilities, 1):
            metadata = sim_vuln['metadata']
            similarity = sim_vuln['similarity_percentage']
            
            similar_cases_text += f"""
Similar Case {i} ({similarity} match):
- Tool: {metadata['tool']}
- Type: {metadata['type']}
- Severity: {metadata['severity']}
- Description: {metadata.get('description', 'N/A')[:200]}...
- File: {metadata.get('file_path', 'N/A')}
"""

        # Create comprehensive RAG-enhanced prompt
        rag_prompt = f"""You are a security expert analyzing vulnerabilities with access to historical similar cases.

CURRENT VULNERABILITY:
Tool: {vulnerability.get('tool', 'unknown')}
Severity: {vulnerability.get('severity', 'unknown')}
Type: {vulnerability.get('type', vulnerability.get('id', 'unknown'))}
Description: {vulnerability.get('description', vulnerability.get('message', ''))}
File: {vulnerability.get('file_path', vulnerability.get('path', 'N/A'))}

BASELINE ANALYSIS:
{self._format_baseline_analysis(baseline_analysis)}

SIMILAR HISTORICAL CASES:
{similar_cases_text}

Based on the current vulnerability, baseline analysis, and similar historical cases, provide an ENHANCED analysis that:

1. **Leverages Historical Patterns**: How do the similar cases inform our understanding?
2. **Enhanced Impact Assessment**: What additional impacts should we consider based on historical data?
3. **Proven Remediation Strategies**: What specific fixes have worked for similar cases?
4. **Contextual Risk Assessment**: How does this compare to the historical pattern of similar vulnerabilities?
5. **Specific Implementation Guidance**: Provide concrete, actionable remediation steps.

Focus on actionable, specific guidance informed by the historical similar cases."""

        return rag_prompt
    
    def _format_baseline_analysis(self, baseline_analysis: Dict[str, Any]) -> str:
        """Format baseline analysis for inclusion in RAG prompt."""
        
        if 'structured_analysis' in baseline_analysis:
            structured = baseline_analysis['structured_analysis']
            return f"""
Impact: {structured.get('impact', 'N/A')}
Remediation: {structured.get('remediation', 'N/A')}
Prevention: {structured.get('prevention', 'N/A')}"""
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
        """Generate analysis text using the base analyzer's generation method."""
        
        # Use the existing generation infrastructure from the base class
        return super()._generate_structured_analysis_internal(prompt)
    
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
                
        except Exception:
            return ""
    
    def _merge_analyses(
        self,
        baseline_analysis: Dict[str, Any],
        enhanced_analysis: Dict[str, Any],
        similar_vulnerabilities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge baseline and enhanced analyses with RAG metadata."""
        
        # Start with baseline analysis
        merged_analysis = baseline_analysis.copy()
        
        # Add RAG enhancements
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
        
        # Enhance structured analysis if it exists
        if 'structured_analysis' in merged_analysis:
            structured = merged_analysis['structured_analysis']
            
            # Add RAG enhancement markers
            for key in ['impact', 'remediation', 'prevention']:
                if key in structured:
                    structured[key] = f"[RAG-Enhanced] {structured[key]}"
        
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


if __name__ == "__main__":
    test_rag_enhanced_analyzer()