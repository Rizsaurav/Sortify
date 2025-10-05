#!/usr/bin/env python3
"""
Startup script for the Sortify RAG system.
Handles initialization, health checks, and service startup.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from typing import Optional

from config import RAGConfig
from rag_system import FastRAG
from document_manager import DocumentManager
from conversion.pdf_converter import PDFConverter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment() -> bool:
    """Check if environment is properly configured."""
    try:
        config = RAGConfig.from_env()
        config.validate()
        
        logger.info(f"✓ Using embedding model: {config.embedding_model_name}")
        logger.info(f"✓ Using LLM model: {config.llm_model_name}")
        
        # Check if documents directory exists
        docs_path = Path(config.documents_dir)
        if not docs_path.exists():
            logger.warning(f"Documents directory not found: {docs_path}")
            docs_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created documents directory: {docs_path}")
        
        # Check if PDF directory exists
        pdf_path = Path("./pdf")
        if pdf_path.exists():
            pdf_files = list(pdf_path.glob("*.pdf")) + list(pdf_path.glob("*.PDF"))
            if pdf_files:
                logger.info(f"✓ Found {len(pdf_files)} PDF file(s) in pdf/ directory")
        
        logger.info("✅ Environment check passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Environment check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def convert_pdfs_to_text() -> dict:
    """Convert PDF files to text before processing."""
    try:
        logger.info("📄 Checking for PDF files to convert...")
        
        config = RAGConfig.from_env()
        converter = PDFConverter(
            pdf_dir="./pdf",
            cache_dir="./storage/pdf_cache",
            output_dir=config.documents_dir
        )
        
        # Convert all PDFs
        stats = converter.convert_all_pdfs()
        
        if stats['total'] > 0:
            logger.info(f"📊 PDF Conversion: {stats['converted']} converted, {stats['skipped']} skipped, {stats['failed']} failed")
            if stats['converted'] > 0:
                logger.info(f"✅ Converted {stats['converted']} PDF(s) to text in {config.documents_dir}")
        else:
            logger.info("📄 No PDF files found in ./pdf directory")
        
        return stats
        
    except Exception as e:
        logger.warning(f"⚠️  PDF conversion encountered an issue: {e}")
        logger.info("Continuing with existing text files...")
        return {'total': 0, 'converted': 0, 'skipped': 0, 'failed': 0}

def initialize_rag_system() -> Optional[FastRAG]:
    """Initialize the RAG system."""
    try:
        logger.info("🚀 Initializing RAG system...")
        
        # Convert PDFs first
        convert_pdfs_to_text()
        
        config = RAGConfig.from_env()
        rag = FastRAG(config)
        
        # Process documents
        stats = rag.process_documents()
        
        logger.info(f"✅ RAG system initialized successfully")
        logger.info(f"📊 Processed {stats['documents']} documents into {stats['chunks']} chunks")
        logger.info(f"⏱️  Processing time: {stats['processing_time']:.2f}s")
        
        return rag
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG system: {e}")
        return None

def run_interactive_mode(rag: FastRAG):
    """Run interactive Q&A mode (basic)."""
    logger.info("🤖 Starting basic interactive mode")
    logger.info("Type 'quit' to exit")
    
    try:
        rag.interactive_qa()
    except KeyboardInterrupt:
        logger.info("👋 Interactive mode terminated")

def run_terminal_qa():
    """Run the enhanced terminal Q&A interface."""
    try:
        logger.info("🎓 Starting enhanced terminal Q&A interface...")
        
        # Convert PDFs before starting terminal
        convert_pdfs_to_text()
        
        from qa_terminal import QATerminal
        terminal = QATerminal()
        terminal.run_interactive()
        
    except ImportError as e:
        logger.error(f"❌ Failed to import terminal Q&A: {e}")
        logger.error("Falling back to basic interactive mode...")
        
        # Fallback to basic mode
        config = RAGConfig.from_env()
        rag = FastRAG(config)
        rag.process_documents()
        run_interactive_mode(rag)
        
    except Exception as e:
        logger.error(f"❌ Failed to start terminal Q&A: {e}")

def run_api_service():
    """Run the API service."""
    try:
        logger.info("🌐 Starting API service...")
        
        # Convert PDFs before starting API
        convert_pdfs_to_text()
        
        from api_service import run_api
        run_api()
        
    except ImportError as e:
        logger.error(f"❌ Failed to import API service: {e}")
        logger.error("Make sure FastAPI and uvicorn are installed: pip install fastapi uvicorn")
    except Exception as e:
        logger.error(f"❌ Failed to start API service: {e}")

def run_examples():
    """Run example usage."""
    try:
        logger.info("📚 Running examples...")
        
        from examples import main as run_examples_main
        run_examples_main()
        
    except Exception as e:
        logger.error(f"❌ Failed to run examples: {e}")

def create_sample_documents():
    """Create sample documents for testing."""
    try:
        from examples import create_sample_documents
        files = create_sample_documents()
        
        if files:
            logger.info(f"📄 Created {len(files)} sample documents")
        else:
            logger.info("📄 Sample documents already exist")
            
    except Exception as e:
        logger.error(f"❌ Failed to create sample documents: {e}")

def main():
    """Main startup function."""
    parser = argparse.ArgumentParser(
        description="Sortify RAG System Startup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  terminal    - Enhanced terminal Q&A interface (RECOMMENDED for students)
  api         - Start API service for frontend integration
  interactive - Basic interactive Q&A mode
  examples    - Run example usage
  init        - Initialize system only

Examples:
  python start.py                          # Start API (default)
  python start.py --mode terminal          # Start terminal Q&A
  python start.py --mode api               # Start API service
  python start.py --check-only             # Check environment only
  python start.py --create-samples         # Create sample documents
        """
    )
    parser.add_argument('--mode', choices=['terminal', 'api', 'interactive', 'examples', 'init'], 
                       default='api', help='Startup mode (default: api)')
    parser.add_argument('--check-only', action='store_true', 
                       help='Only check environment, don\'t start services')
    parser.add_argument('--create-samples', action='store_true',
                       help='Create sample documents')
    parser.add_argument('--skip-init', action='store_true',
                       help='Skip RAG system initialization')
    
    args = parser.parse_args()
    
    print("🎓 SORTIFY RAG SYSTEM")
    print("="*50)
    
    # Check environment
    if not check_environment():
        logger.error("❌ Environment check failed. Please fix the issues above.")
        sys.exit(1)
    
    if args.check_only:
        logger.info("✅ Environment check completed successfully")
        return
    
    # Create sample documents if requested
    if args.create_samples:
        create_sample_documents()
    
    # Initialize RAG system (unless skipped)
    rag = None
    if not args.skip_init and args.mode not in ['examples', 'terminal']:
        rag = initialize_rag_system()
        if not rag:
            logger.error("❌ Failed to initialize RAG system")
            sys.exit(1)
    
    # Run based on mode
    try:
        if args.mode == 'terminal':
            # Terminal mode handles its own initialization
            run_terminal_qa()
            
        elif args.mode == 'api':
            run_api_service()
            
        elif args.mode == 'interactive':
            if not rag:
                logger.error("❌ RAG system not initialized")
                sys.exit(1)
            run_interactive_mode(rag)
            
        elif args.mode == 'examples':
            run_examples()
            
        elif args.mode == 'init':
            logger.info("✅ Initialization completed")
            
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
