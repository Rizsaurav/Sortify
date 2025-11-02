"""
Embedding Generator for Training Data
======================================
Generates embeddings for all documents in robust_documents.json

Uses your production embedding service (loads cached model from config)
Output: training_data_with_embeddings.json (ready for classifier training)
"""

import json
import sys
import os
import numpy as np
from typing import List, Dict, Any
import time
from tqdm import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.embedding_service import get_embedding_service


class EmbeddingGenerator:
    """Generate embeddings for training documents using production embedding service."""
    
    def __init__(self):
        """Initialize using production embedding service."""
        print(f"Loading production embedding service from config...")
        
        self.embedding_service = get_embedding_service()
        model_info = self.embedding_service.get_model_info()
        
        print(f"Model loaded: {model_info['model_name']}")
        print(f"Dimension: {model_info['dimension']}")
        print(f"Device: {model_info['device']}")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single document.
        
        Args:
            text: Document text
            
        Returns:
            Embedding vector as numpy array
        """
        # Use production embedding service
        embedding = self.embedding_service.encode_document(text)
        return embedding
    
    def process_documents(
        self,
        input_file: str = "robust_documents.json",
        output_file: str = "training_data_with_embeddings.json"
    ) -> List[Dict[str, Any]]:
        """
        Process all documents and add embeddings.
        
        Args:
            input_file: Input JSON with documents
            output_file: Output JSON with embeddings added
            
        Returns:
            List of documents with embeddings
        """
        print(f"\nLoading documents from: {input_file}")
        
        # Load documents
        with open(input_file, 'r') as f:
            documents = json.load(f)
        
        print(f"Loaded {len(documents)} documents")
        
        # Process each document
        print(f"\nGenerating embeddings...")
        training_data = []
        
        start_time = time.time()
        
        for i, doc in enumerate(tqdm(documents, desc="Processing")):
            # Generate embedding using production service
            embedding = self.generate_embedding(doc['content'])
            
            # Create training data entry
            training_entry = {
                'filename': doc['filename'],
                'content': doc['content'],
                'embedding': embedding.tolist(),  # Convert to list for JSON
                'category': doc['category']
            }
            
            training_data.append(training_entry)
        
        elapsed = time.time() - start_time
        
        print(f"\nGenerated {len(training_data)} embeddings in {elapsed:.1f}s")
        print(f"Average: {elapsed / len(training_data):.3f}s per document")
        
        # Save to file
        print(f"\nSaving to: {output_file}")
        with open(output_file, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        print(f"Saved!")
        
        # Show statistics
        self._show_stats(training_data)
        
        return training_data
    
    def _show_stats(self, training_data: List[Dict]):
        """Show statistics about the training data."""
        from collections import Counter
        
        categories = [d['category'] for d in training_data]
        counts = Counter(categories)
        
        total_words = sum(len(d['content'].split()) for d in training_data)
        avg_words = total_words / len(training_data)
        
        # Check embedding dimensions
        embedding_dims = [len(d['embedding']) for d in training_data]
        
        print(f"\nTraining Data Statistics:")
        print(f"   Total documents: {len(training_data)}")
        print(f"   Unique categories: {len(counts)}")
        print(f"   Embedding dimension: {embedding_dims[0]}")
        print(f"   Total words: {total_words:,}")
        print(f"   Average words per doc: {avg_words:.0f}")
        
        # Check all embeddings have same dimension
        if len(set(embedding_dims)) != 1:
            print(f"   WARNING: Inconsistent embedding dimensions!")
        else:
            print(f"   All embeddings have consistent dimensions")
        
        print(f"\nTop 20 Categories:")
        for cat, count in counts.most_common(20):
            print(f"   {cat}: {count}")
        
        if len(counts) > 20:
            print(f"   ... and {len(counts) - 20} more categories")
        
        print(f"\nTraining data ready for classifier training!")


def main():
    """Main pipeline."""
    print("=" * 60)
    print("EMBEDDING GENERATOR")
    print("=" * 60)
    print("\nUsing PRODUCTION embedding service from config\n")
    
    try:
        # Initialize generator (uses production config)
        generator = EmbeddingGenerator()
        
        # Process documents
        training_data = generator.process_documents(
            input_file="robust_documents.json",
            output_file="training_data_with_embeddings.json"
        )
        
        print("\n" + "=" * 60)
        print("EMBEDDING GENERATION COMPLETE!")
        print("=" * 60)
        print("\nNext Steps:")
        print("1. Review training_data_with_embeddings.json")
        print("2. Run: python train_classifier.py")
        print("3. Deploy your classifier for production!")
        
    except FileNotFoundError:
        print("\nError: robust_documents.json not found!")
        print("\nMake sure:")
        print("  1. You've run ollama_document_generator_v2.py first")
        print("  2. The file robust_documents.json exists in current directory")
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

    
    def process_documents(
        self,
        input_file: str = "robust_documents.json",
        output_file: str = "training_data_with_embeddings.json"
    ) -> List[Dict[str, Any]]:
        """
        Process all documents and add embeddings.
        
        Args:
            input_file: Input JSON with documents
            output_file: Output JSON with embeddings added
            
        Returns:
            List of documents with embeddings
        """
        print(f"\nLoading documents from: {input_file}")
        
        # Load documents
        with open(input_file, 'r') as f:
            documents = json.load(f)
        
        print(f"Loaded {len(documents)} documents")
        
        # Process each document
        print(f"\nGenerating embeddings...")
        training_data = []
        
        start_time = time.time()
        
        for i, doc in enumerate(tqdm(documents, desc="Processing")):
            # Generate embedding (same as production)
            embedding = self.generate_embedding(doc['content'])
            
            # Create training data entry
            training_entry = {
                'filename': doc['filename'],
                'content': doc['content'],
                'embedding': embedding.tolist(),  # Convert to list for JSON
                'category': doc['category']
            }
            
            training_data.append(training_entry)
        
        elapsed = time.time() - start_time
        
        print(f"\nGenerated {len(training_data)} embeddings in {elapsed:.1f}s")
        print(f"Average: {elapsed / len(training_data):.3f}s per document")
        
        # Save to file
        print(f"\nSaving to: {output_file}")
        with open(output_file, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        print(f"Saved!")
        
        # Show statistics
        self._show_stats(training_data)
        
        return training_data
    
    def _show_stats(self, training_data: List[Dict]):
        """Show statistics about the training data."""
        from collections import Counter
        
        categories = [d['category'] for d in training_data]
        counts = Counter(categories)
        
        total_words = sum(len(d['content'].split()) for d in training_data)
        avg_words = total_words / len(training_data)
        
        # Check embedding dimensions
        embedding_dims = [len(d['embedding']) for d in training_data]
        
        print(f"\nTraining Data Statistics:")
        print(f"   Total documents: {len(training_data)}")
        print(f"   Unique categories: {len(counts)}")
        print(f"   Embedding dimension: {embedding_dims[0]} (production: 1024)")
        print(f"   Total words: {total_words:,}")
        print(f"   Average words per doc: {avg_words:.0f}")
        
        # Check all embeddings have same dimension
        if len(set(embedding_dims)) != 1:
            print(f"   WARNING: Inconsistent embedding dimensions!")
        else:
            print(f"   All embeddings have consistent dimensions")
        
        print(f"\nTop 20 Categories:")
        for cat, count in counts.most_common(20):
            print(f"   {cat}: {count}")
        
        if len(counts) > 20:
            print(f"   ... and {len(counts) - 20} more categories")
        
        print(f"\nTraining data ready for classifier training!")


def main():
    """Main pipeline."""
    print("=" * 60)
    print("EMBEDDING GENERATOR")
    print("=" * 60)

    
    try:
        # Initialize generator
        generator = EmbeddingGenerator(model_name="Qwen/Qwen3-Embedding-0.6B")
        
        # Process documents
        training_data = generator.process_documents(
            input_file="robust_documents.json",
            output_file="training_data_with_embeddings.json"
        )
        
        print("\n" + "=" * 60)
        print("EMBEDDING GENERATION COMPLETE!")
        print("=" * 60)
        
    except FileNotFoundError:
        print("\nError: robust_documents.json not found!")
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()