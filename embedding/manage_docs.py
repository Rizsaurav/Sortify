#!/usr/bin/env python3
"""
Document management utility for Sortify RAG System.
Easily add, remove, and manage study documents.

Features:
- Add single or multiple documents
- Support for .txt, .md, and other text formats
- Automatic reprocessing after changes
- Document validation and stats
"""

import sys
import os
import shutil
from pathlib import Path
from typing import List, Optional
import argparse

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import RAGConfig
from rag_system import FastRAG
from document_manager import DocumentManager

class Colors:
    """Terminal colors."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def colored(text: str, color: str) -> str:
    """Return colored text."""
    return f"{color}{text}{Colors.END}"

class DocumentManagerCLI:
    """CLI for managing documents."""
    
    def __init__(self):
        """Initialize document manager."""
        self.config = RAGConfig.from_env()
        self.docs_dir = Path(self.config.documents_dir)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.doc_manager = DocumentManager(str(self.docs_dir))
    
    def list_documents(self):
        """List all documents in the system."""
        print(colored("\n📚 Documents in System", Colors.BOLD + Colors.CYAN))
        print("=" * 70)
        
        try:
            documents = self.doc_manager.list_documents()
            
            if not documents:
                print(colored("  No documents found. Add some with 'add' command.", Colors.YELLOW))
                return
            
            print(f"\nFound {colored(str(len(documents)), Colors.GREEN)} documents:\n")
            
            for i, doc_name in enumerate(documents, 1):
                doc_path = self.docs_dir / doc_name
                
                # Get file stats
                if doc_path.exists():
                    size = doc_path.stat().st_size
                    size_kb = size / 1024
                    
                    # Read file to get word count
                    try:
                        with open(doc_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            word_count = len(content.split())
                    except:
                        word_count = 0
                    
                    print(f"  {i}. {colored(doc_name, Colors.BOLD)}")
                    print(f"     Size: {size_kb:.1f} KB | Words: {word_count:,}")
                else:
                    print(f"  {i}. {colored(doc_name, Colors.BOLD)} {colored('(missing)', Colors.RED)}")
            
            print()
            
        except Exception as e:
            print(colored(f"  Error listing documents: {e}", Colors.RED))
    
    def add_document(self, source_path: str, dest_name: Optional[str] = None):
        """Add a document to the system."""
        try:
            source = Path(source_path)
            
            if not source.exists():
                print(colored(f"  ✗ File not found: {source_path}", Colors.RED))
                return False
            
            if not source.is_file():
                print(colored(f"  ✗ Not a file: {source_path}", Colors.RED))
                return False
            
            # Determine destination name
            if dest_name:
                dest_name = dest_name if dest_name.endswith('.txt') else f"{dest_name}.txt"
            else:
                dest_name = source.name
            
            dest_path = self.docs_dir / dest_name
            
            # Check if file already exists
            if dest_path.exists():
                response = input(colored(f"  ⚠️  {dest_name} already exists. Overwrite? (y/n): ", Colors.YELLOW))
                if response.lower() != 'y':
                    print(colored("  Cancelled.", Colors.YELLOW))
                    return False
            
            # Copy file
            shutil.copy2(source, dest_path)
            
            # Get file stats
            size_kb = dest_path.stat().st_size / 1024
            with open(dest_path, 'r', encoding='utf-8', errors='ignore') as f:
                word_count = len(f.read().split())
            
            print(colored(f"  ✓ Added: {dest_name}", Colors.GREEN))
            print(f"    Size: {size_kb:.1f} KB | Words: {word_count:,}")
            
            return True
            
        except Exception as e:
            print(colored(f"  ✗ Error adding document: {e}", Colors.RED))
            return False
    
    def add_multiple_documents(self, source_paths: List[str]):
        """Add multiple documents."""
        print(colored(f"\n📥 Adding {len(source_paths)} documents...", Colors.CYAN))
        print("-" * 70)
        
        success_count = 0
        for source_path in source_paths:
            print(f"\n  Processing: {source_path}")
            if self.add_document(source_path):
                success_count += 1
        
        print(f"\n{'-' * 70}")
        print(colored(f"✓ Successfully added {success_count}/{len(source_paths)} documents", Colors.GREEN))
        
        return success_count
    
    def remove_document(self, doc_name: str):
        """Remove a document from the system."""
        try:
            success = self.doc_manager.delete_document(doc_name)
            
            if success:
                print(colored(f"  ✓ Removed: {doc_name}", Colors.GREEN))
                return True
            else:
                print(colored(f"  ✗ Document not found: {doc_name}", Colors.RED))
                return False
                
        except Exception as e:
            print(colored(f"  ✗ Error removing document: {e}", Colors.RED))
            return False
    
    def create_sample_documents(self):
        """Create sample documents for testing."""
        print(colored("\n📝 Creating sample documents...", Colors.CYAN))
        print("-" * 70)
        
        samples = {
            "machine_learning.txt": """Machine Learning Overview

Machine Learning (ML) is a subset of artificial intelligence that focuses on building systems that can learn from and make decisions based on data. Instead of being explicitly programmed for every task, ML systems improve their performance through experience.

Types of Machine Learning:

1. Supervised Learning: The algorithm learns from labeled training data. Examples include classification (identifying spam emails) and regression (predicting house prices).

2. Unsupervised Learning: The algorithm finds patterns in unlabeled data. Common techniques include clustering (customer segmentation) and dimensionality reduction.

3. Reinforcement Learning: An agent learns to make decisions by receiving rewards or penalties for actions taken in an environment.

Key Concepts:
- Training Data: The dataset used to train the model
- Features: Input variables used for predictions
- Labels: Output variables (in supervised learning)
- Model: The mathematical representation learned from data
- Validation: Testing model performance on unseen data

Applications: Image recognition, natural language processing, recommendation systems, autonomous vehicles, fraud detection, and medical diagnosis.
""",

            "deep_learning.txt": """Deep Learning Fundamentals

Deep Learning is a specialized subset of machine learning that uses artificial neural networks with multiple layers (hence "deep") to model complex patterns in data.

Neural Network Architecture:
- Input Layer: Receives the raw data
- Hidden Layers: Process information through multiple transformations
- Output Layer: Produces the final prediction

Key Components:
1. Neurons: Basic computational units that apply activation functions
2. Weights: Parameters that the network learns during training
3. Biases: Additional parameters to improve model flexibility
4. Activation Functions: Non-linear functions (ReLU, sigmoid, tanh)
5. Backpropagation: Algorithm for updating weights based on errors

Popular Architectures:
- Convolutional Neural Networks (CNNs): Excellent for image processing
- Recurrent Neural Networks (RNNs): Great for sequential data like text
- Transformers: State-of-the-art for natural language processing
- GANs: Generate new data similar to training data

Training Process:
1. Forward pass: Input data flows through the network
2. Loss calculation: Measure error between prediction and actual
3. Backward pass: Calculate gradients using backpropagation
4. Weight update: Adjust parameters to minimize loss

Applications: Computer vision, speech recognition, language translation, game playing, and generative AI.
""",

            "study_tips.txt": """Effective Study Techniques for Computer Science

Active Learning Strategies:

1. Spaced Repetition: Review material at increasing intervals
   - Use flashcards for terminology
   - Practice coding problems daily
   - Revisit concepts weekly

2. Practice Coding: The most important skill for CS
   - Work on small projects
   - Solve algorithm problems
   - Contribute to open source
   - Build a portfolio

3. Explain Concepts: Teaching solidifies understanding
   - Write blog posts about what you learn
   - Explain to study partners
   - Create tutorial videos
   - Answer questions on forums

4. Break Down Complex Topics:
   - Start with fundamentals
   - Build up to advanced concepts
   - Use diagrams and visualizations
   - Connect to real-world examples

Time Management:
- Pomodoro Technique: 25-minute focused sessions
- Schedule specific times for different subjects
- Take regular breaks to avoid burnout
- Prioritize difficult topics when you're fresh

Resources:
- Online courses (Coursera, edX, Udemy)
- Documentation and official guides
- Stack Overflow and developer communities
- GitHub for code examples
- YouTube tutorials for visual learning

Debugging Skills:
- Read error messages carefully
- Use print statements strategically
- Learn to use debuggers
- Test code incrementally
- Write unit tests

Remember: Consistency beats intensity. Regular, focused study sessions are more effective than cramming!
"""
        }
        
        created_count = 0
        for filename, content in samples.items():
            file_path = self.docs_dir / filename
            
            if file_path.exists():
                print(f"  - {filename} {colored('(exists)', Colors.YELLOW)}")
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                print(f"  {colored('✓', Colors.GREEN)} Created: {filename}")
                created_count += 1
        
        print(f"\n{colored(f'Created {created_count} new sample documents', Colors.GREEN)}")
        return created_count
    
    def reprocess_documents(self):
        """Reprocess all documents to update embeddings."""
        print(colored("\n🔄 Reprocessing documents...", Colors.CYAN))
        print("-" * 70)
        
        try:
            rag = FastRAG(self.config)
            stats = rag.process_documents(force_reprocess=True)
            
            print(colored(f"\n✓ Reprocessing complete!", Colors.GREEN))
            print(f"  Documents: {stats['documents']}")
            print(f"  Chunks: {stats['chunks']}")
            print(f"  Time: {stats['processing_time']:.2f}s")
            
            return True
            
        except Exception as e:
            print(colored(f"\n✗ Error reprocessing: {e}", Colors.RED))
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Sortify RAG Document Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_docs.py list                        # List all documents
  python manage_docs.py add path/to/file.txt        # Add a document
  python manage_docs.py add file.txt --name notes   # Add with custom name
  python manage_docs.py remove notes.txt            # Remove a document
  python manage_docs.py samples                     # Create sample documents
  python manage_docs.py reprocess                   # Reprocess all documents
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    subparsers.add_parser('list', help='List all documents')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add document(s)')
    add_parser.add_argument('files', nargs='+', help='File(s) to add')
    add_parser.add_argument('--name', help='Custom name for single file')
    add_parser.add_argument('--no-reprocess', action='store_true', help='Skip reprocessing')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a document')
    remove_parser.add_argument('filename', help='Document to remove')
    remove_parser.add_argument('--no-reprocess', action='store_true', help='Skip reprocessing')
    
    # Samples command
    subparsers.add_parser('samples', help='Create sample documents')
    
    # Reprocess command
    subparsers.add_parser('reprocess', help='Reprocess all documents')
    
    args = parser.parse_args()
    
    # Create manager
    manager = DocumentManagerCLI()
    
    # Print header
    print("\n" + "="*70)
    print(colored("📚 SORTIFY RAG - Document Manager", Colors.BOLD + Colors.CYAN))
    print("="*70)
    
    # Handle commands
    if args.command == 'list' or not args.command:
        manager.list_documents()
    
    elif args.command == 'add':
        if len(args.files) == 1:
            success = manager.add_document(args.files[0], args.name)
        else:
            if args.name:
                print(colored("  ⚠️  --name can only be used with single file", Colors.YELLOW))
            success = manager.add_multiple_documents(args.files) > 0
        
        if success and not args.no_reprocess:
            manager.reprocess_documents()
    
    elif args.command == 'remove':
        success = manager.remove_document(args.filename)
        
        if success and not args.no_reprocess:
            manager.reprocess_documents()
    
    elif args.command == 'samples':
        created = manager.create_sample_documents()
        
        if created > 0:
            response = input(colored("\n  Reprocess documents now? (y/n): ", Colors.YELLOW))
            if response.lower() == 'y':
                manager.reprocess_documents()
    
    elif args.command == 'reprocess':
        manager.reprocess_documents()
    
    else:
        parser.print_help()
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colored("\n\n⚠️  Interrupted by user", Colors.YELLOW))
        sys.exit(0)
    except Exception as e:
        print(colored(f"\n❌ Error: {e}", Colors.RED))
        import traceback
        traceback.print_exc()
        sys.exit(1)

