#!/usr/bin/env python3
"""
Local Security Knowledge Base with FAISS Vector Storage

This module implements Phase 2 of the AI Security Enhancement plan:
- Local FAISS-based vector storage for vulnerability knowledge
- Open-source embeddings using sentence-transformers
- RAG-enhanced vulnerability analysis capabilities
- Integration with existing vulnerability processing pipeline

Author: AI Security Enhancement System
Created: 2025-09-16
"""

import os
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

# Fix HuggingFace tokenizers parallelism warning
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# RAG dependencies
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Project dependencies
from config_manager import OLMoSecurityConfig


class LocalSecurityKnowledgeBase:
    """
    Local knowledge base for security vulnerabilities using FAISS vector storage.
    
    This class implements the RAG (Retrieval-Augmented Generation) knowledge base
    for enhancing vulnerability analysis with similar historical cases and patterns.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the local security knowledge base."""
        
        # Configuration
        self.config = OLMoSecurityConfig()
        # Determine project root from data directory
        self.project_root = project_root or Path(self.config.data_dir).parent.parent
        
        # Knowledge base directories
        self.knowledge_base_dir = self.project_root / "security-ai-analysis" / "knowledge_base"
        self.embeddings_dir = self.knowledge_base_dir / "embeddings"
        self.code_examples_dir = self.knowledge_base_dir / "code_examples"
        
        # Ensure directories exist
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        self.code_examples_dir.mkdir(parents=True, exist_ok=True)
        
        # Embedding model (open-source, runs locally)
        self.embeddings_model = None
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
        
        # FAISS index and metadata
        self.vector_index = None
        self.vulnerability_metadata = []
        
        # File paths for persistence
        self.index_file_path = self.embeddings_dir / "vulnerability_index.faiss"
        self.metadata_file_path = self.embeddings_dir / "vulnerability_metadata.json"
        self.embeddings_cache_path = self.embeddings_dir / "embeddings_cache.pkl"
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def _initialize_embeddings_model(self):
        """Initialize the sentence transformer model for embeddings."""
        
        if self.embeddings_model is None:
            try:
                # Use a lightweight, fast model that works well for security text
                self.embeddings_model = SentenceTransformer(
                    'all-MiniLM-L6-v2',
                    device='cpu'  # Ensure CPU usage for compatibility
                )
                self.logger.info("✅ Initialized SentenceTransformer model: all-MiniLM-L6-v2")
                
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize embeddings model: {e}")
                raise
    
    def build_knowledge_base_from_results(self, vulnerability_results: List[Dict[str, Any]]):
        """
        Build the knowledge base from existing vulnerability analysis results.
        
        Args:
            vulnerability_results: List of vulnerability analysis results from existing pipeline
        """
        
        self.logger.info("🚀 Building security knowledge base from vulnerability results...")
        
        # Initialize embeddings model
        self._initialize_embeddings_model()
        
        # Prepare vulnerability data for embedding
        vulnerability_texts = []
        vulnerability_metadata = []
        
        processed_count = 0
        successful_count = 0
        
        for result in vulnerability_results:
            processed_count += 1
            
            try:
                # Extract vulnerability information
                vulnerability = result.get('vulnerability', {})
                analysis = result.get('analysis', {})
                
                if not vulnerability or not analysis:
                    continue
                    
                # Create comprehensive text representation for embedding
                vulnerability_text_parts = [
                    f"Tool: {vulnerability.get('tool', 'unknown')}",
                    f"Severity: {vulnerability.get('severity', 'unknown')}",
                    f"Type: {vulnerability.get('type', vulnerability.get('id', 'unknown'))}",
                    f"Description: {vulnerability.get('description', vulnerability.get('message', ''))}",
                    f"File: {vulnerability.get('file_path', vulnerability.get('path', 'N/A'))}"
                ]
                
                # Add analysis content if available
                if isinstance(analysis, dict):
                    structured_analysis = analysis.get('structured_analysis', {})
                    if structured_analysis:
                        vulnerability_text_parts.extend([
                            f"Impact: {structured_analysis.get('impact', '')}",
                            f"Remediation: {structured_analysis.get('remediation', '')}",
                            f"Prevention: {structured_analysis.get('prevention', '')}"
                        ])
                
                # Combine into single text for embedding
                vulnerability_text = " ".join(filter(None, vulnerability_text_parts))
                
                if not vulnerability_text.strip():
                    continue
                
                vulnerability_texts.append(vulnerability_text)
                
                # Prepare metadata
                metadata = {
                    'id': vulnerability.get('id', f"vuln_{processed_count}"),
                    'tool': vulnerability.get('tool', 'unknown'),
                    'severity': vulnerability.get('severity', 'unknown'),
                    'type': vulnerability.get('type', vulnerability.get('id', 'unknown')),
                    'file_path': vulnerability.get('file_path', vulnerability.get('path', '')),
                    'description': vulnerability.get('description', vulnerability.get('message', '')),
                    'has_analysis': bool(analysis),
                    'has_code_context': bool(vulnerability.get('file_path')),
                    'indexed_at': datetime.now().isoformat(),
                    'original_index': processed_count - 1  # Reference to original results
                }
                
                vulnerability_metadata.append(metadata)
                successful_count += 1
                
            except Exception as e:
                self.logger.warning(f"⚠️ Skipped vulnerability {processed_count}: {e}")
                continue
        
        if not vulnerability_texts:
            raise ValueError("No valid vulnerability data found for knowledge base creation")
        
        self.logger.info(f"📊 Prepared {successful_count}/{processed_count} vulnerabilities for embedding")
        
        # Generate embeddings
        self.logger.info("🧠 Generating embeddings...")
        embeddings = self._generate_embeddings(vulnerability_texts)
        
        # Create and populate FAISS index
        self._create_vector_index(embeddings, vulnerability_metadata)
        
        # Save to disk
        self._save_knowledge_base()
        
        self.logger.info(f"✅ Knowledge base built successfully with {len(vulnerability_metadata)} entries")
        
        return {
            'total_processed': processed_count,
            'successful_embeddings': successful_count,
            'knowledge_base_size': len(vulnerability_metadata),
            'embedding_dimension': self.embedding_dimension
        }
    
    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        
        try:
            # Generate embeddings in batches for efficiency
            batch_size = 32
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.embeddings_model.encode(
                    batch_texts,
                    show_progress_bar=True,
                    batch_size=batch_size
                )
                all_embeddings.append(batch_embeddings)
                
                if i % (batch_size * 5) == 0:  # Progress update every 5 batches
                    self.logger.info(f"🔄 Generated embeddings for {min(i + batch_size, len(texts))}/{len(texts)} texts")
            
            # Combine all embeddings
            embeddings = np.vstack(all_embeddings)
            
            self.logger.info(f"✅ Generated embeddings shape: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate embeddings: {e}")
            raise
    
    def _create_vector_index(self, embeddings: np.ndarray, metadata: List[Dict]):
        """Create and populate FAISS vector index."""
        
        try:
            # Create FAISS index (Inner Product similarity)
            self.vector_index = faiss.IndexFlatIP(self.embedding_dimension)
            
            # Normalize embeddings for cosine similarity (IP with normalized vectors = cosine similarity)
            embeddings_normalized = embeddings.astype('float32')
            faiss.normalize_L2(embeddings_normalized)
            
            # Add embeddings to index
            self.vector_index.add(embeddings_normalized)
            self.vulnerability_metadata = metadata
            
            self.logger.info(f"✅ Created FAISS index with {self.vector_index.ntotal} vectors")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create vector index: {e}")
            raise
    
    def _save_knowledge_base(self):
        """Save the knowledge base to disk."""
        
        try:
            # Save FAISS index
            faiss.write_index(self.vector_index, str(self.index_file_path))
            
            # Save metadata
            with open(self.metadata_file_path, 'w') as f:
                json.dump(self.vulnerability_metadata, f, indent=2)
            
            # Save embeddings cache (optional, for faster reloading)
            cache_data = {
                'embedding_dimension': self.embedding_dimension,
                'model_name': 'all-MiniLM-L6-v2',
                'created_at': datetime.now().isoformat(),
                'total_vectors': self.vector_index.ntotal
            }
            
            with open(self.embeddings_cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            self.logger.info(f"💾 Saved knowledge base to {self.embeddings_dir}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save knowledge base: {e}")
            raise
    
    def load_knowledge_base(self) -> bool:
        """
        Load existing knowledge base from disk.
        
        Returns:
            bool: True if knowledge base loaded successfully, False otherwise
        """
        
        try:
            # Check if knowledge base files exist
            if not (self.index_file_path.exists() and self.metadata_file_path.exists()):
                self.logger.info("📂 No existing knowledge base found")
                return False
            
            # Initialize embeddings model
            self._initialize_embeddings_model()
            
            # Load FAISS index
            self.vector_index = faiss.read_index(str(self.index_file_path))
            
            # Load metadata
            with open(self.metadata_file_path, 'r') as f:
                self.vulnerability_metadata = json.load(f)
            
            self.logger.info(f"✅ Loaded knowledge base with {self.vector_index.ntotal} vectors")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load knowledge base: {e}")
            return False
    
    def find_similar_vulnerabilities(
        self, 
        query_vulnerability: Dict[str, Any], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar vulnerabilities using vector similarity search.
        
        Args:
            query_vulnerability: Vulnerability to find similar cases for
            top_k: Number of similar vulnerabilities to return
            
        Returns:
            List of similar vulnerabilities with similarity scores
        """
        
        if self.vector_index is None:
            if not self.load_knowledge_base():
                raise RuntimeError("Knowledge base not available. Please build it first.")
        
        try:
            # Create query text representation
            query_text_parts = [
                f"Tool: {query_vulnerability.get('tool', 'unknown')}",
                f"Severity: {query_vulnerability.get('severity', 'unknown')}",
                f"Type: {query_vulnerability.get('type', query_vulnerability.get('id', 'unknown'))}",
                f"Description: {query_vulnerability.get('description', query_vulnerability.get('message', ''))}",
            ]
            
            query_text = " ".join(filter(None, query_text_parts))
            
            if not query_text.strip():
                self.logger.warning("Empty query text for similarity search")
                return []
            
            # Generate query embedding
            query_embedding = self.embeddings_model.encode([query_text])
            
            # Normalize for cosine similarity
            query_embedding_normalized = query_embedding.astype('float32')
            faiss.normalize_L2(query_embedding_normalized)
            
            # Search for similar vectors
            scores, indices = self.vector_index.search(query_embedding_normalized, top_k)
            
            # Format results
            similar_vulnerabilities = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.vulnerability_metadata):
                    similar_vuln = {
                        'metadata': self.vulnerability_metadata[idx],
                        'similarity_score': float(score),
                        'similarity_percentage': f"{float(score) * 100:.1f}%"
                    }
                    similar_vulnerabilities.append(similar_vuln)
            
            self.logger.info(f"🔍 Found {len(similar_vulnerabilities)} similar vulnerabilities")
            return similar_vulnerabilities
            
        except Exception as e:
            self.logger.error(f"❌ Failed to find similar vulnerabilities: {e}")
            return []
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        
        if self.vector_index is None:
            if not self.load_knowledge_base():
                return {"status": "not_available", "total_vectors": 0}
        
        # Analyze metadata for statistics
        tool_counts = {}
        severity_counts = {}
        type_counts = {}
        
        for metadata in self.vulnerability_metadata:
            tool = metadata.get('tool', 'unknown')
            severity = metadata.get('severity', 'unknown')
            vuln_type = metadata.get('type', 'unknown')
            
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            type_counts[vuln_type] = type_counts.get(vuln_type, 0) + 1
        
        return {
            "status": "available",
            "total_vectors": self.vector_index.ntotal,
            "embedding_dimension": self.embedding_dimension,
            "model_name": "all-MiniLM-L6-v2",
            "index_file_size": self.index_file_path.stat().st_size if self.index_file_path.exists() else 0,
            "metadata_file_size": self.metadata_file_path.stat().st_size if self.metadata_file_path.exists() else 0,
            "tool_distribution": dict(sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)),
            "severity_distribution": dict(sorted(severity_counts.items(), key=lambda x: x[1], reverse=True)),
            "type_distribution": dict(sorted(list(type_counts.items())[:10], key=lambda x: x[1], reverse=True)),  # Top 10
            "storage_directory": str(self.embeddings_dir)
        }
    
    def search_by_text(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search knowledge base using free-form text query.
        
        Args:
            query_text: Text to search for
            top_k: Number of results to return
            
        Returns:
            List of matching vulnerabilities with similarity scores
        """
        
        if not query_text.strip():
            return []
        
        # Create a fake vulnerability object for the similarity search
        query_vulnerability = {
            'description': query_text,
            'type': 'text_search',
            'tool': 'manual_query'
        }
        
        return self.find_similar_vulnerabilities(query_vulnerability, top_k)


def test_knowledge_base():
    """Test function for the LocalSecurityKnowledgeBase."""
    
    print("🧪 Testing LocalSecurityKnowledgeBase...")
    
    try:
        # Initialize knowledge base
        kb = LocalSecurityKnowledgeBase()
        print("✅ Knowledge base initialized")
        
        # Test loading existing knowledge base
        loaded = kb.load_knowledge_base()
        print(f"📂 Existing knowledge base loaded: {loaded}")
        
        if loaded:
            # Test statistics
            stats = kb.get_knowledge_base_stats()
            print(f"📊 Knowledge base stats: {stats['total_vectors']} vectors")
            print(f"🔧 Tools: {list(stats['tool_distribution'].keys())}")
            
            # Test similarity search
            test_vulnerability = {
                'tool': 'trivy',
                'severity': 'HIGH',
                'type': 'vulnerability',
                'description': 'SQL injection vulnerability in authentication endpoint'
            }
            
            similar = kb.find_similar_vulnerabilities(test_vulnerability, top_k=3)
            print(f"🔍 Found {len(similar)} similar vulnerabilities")
            for i, sim in enumerate(similar, 1):
                print(f"  {i}. {sim['similarity_percentage']} - {sim['metadata']['type']}")
        
        print("✅ Knowledge base test completed successfully")
        
    except Exception as e:
        print(f"❌ Knowledge base test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_knowledge_base()