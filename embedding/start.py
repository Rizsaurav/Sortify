#!/usr/bin/env python3
"""
Main entry point for the Sortify RAG system.
Streamlined PDF processing with better error handling.
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
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def print_banner():
    """Print application banner."""
    print("\n" + "=" * 70)
    print("🎓 SORTIFY RAG SYSTEM")
    print("=" * 70)

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

def convert_pdfs_to_text(force: bool = False) -> dict:
    """
    Convert PDF files to text before processing.
    
    Args:
        force: Force reconversion of all PDFs
        
    Returns:
        Dictionary with conversion statistics
    """
    try:
        logger.info("📄 Checking for PDF files to convert...")
        
        config = RAGConfig.from_env()
        converter = PDFConverter(
            pdf_dir="./pdf",
            cache_dir="./storage/pdf_cache",
            output_dir=config.documents_dir
        )
        
        # Convert all PDFs
        stats = converter.convert_all_pdfs(force=force)
        
        if stats['total'] > 0:
            summary = f"📊 PDF Conversion: {stats['converted']} converted, {stats['skipped']} skipped, {stats['failed']} failed"
            logger.info(summary)
            
            if stats['converted'] > 0:
                logger.info(f"✅ Successfully converted {stats['converted']} PDF(s) to {config.documents_dir}")
            
            if stats['failed'] > 0:
                logger.warning(f"⚠️  {stats['failed']} PDF(s) failed to convert")
                # List failed files
                for file_info in stats.get('files', []):
                    if file_info['status'] == 'failed':
                        logger.warning(f"   - {file_info['name']}")
        else:
            logger.info("📄 No PDF files found in ./pdf directory")
        
        return stats
        
    except Exception as e:
        logger.warning(f"⚠️  PDF conversion error: {e}")
        logger.info("Continuing with existing text files...")
        return {'total': 0, 'converted': 0, 'skipped': 0, 'failed': 0}

def initialize_rag_system() -> Optional[FastRAG]:
    """Initialize the RAG system."""
    try:
        config = RAGConfig.from_env()
        rag = FastRAG(config)
        return rag
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        import traceback
        traceback.print_exc()
        return None

def start_terminal_mode(rag: FastRAG):
    """Start terminal Q&A interface."""
    try:
        from qa_terminal import run_terminal_interface
        logger.info("🎓 Starting enhanced terminal Q&A interface...")
        run_terminal_interface(rag)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"Terminal mode error: {e}")
        import traceback
        traceback.print_exc()

def start_api_mode(host: str = "0.0.0.0", port: int = 8000):
    """Start FastAPI server."""
    try:
        logger.info("🚀 Starting FastAPI server...")
        from api_service import app
        import uvicorn
        uvicorn.run(app, host=host, port=port)
    except ImportError:
        logger.error("FastAPI/Uvicorn not installed. Install with: pip install fastapi uvicorn")
    except Exception as e:
        logger.error(f"API mode error: {e}")
        import traceback
        traceback.print_exc()

def list_pdfs():
    """List all PDFs and their conversion status."""
    try:
        config = RAGConfig.from_env()
        converter = PDFConverter(
            pdf_dir="./pdf",
            cache_dir="./storage/pdf_cache",
            output_dir=config.documents_dir
        )
        
        pdfs = converter.list_pdfs()
        
        if not pdfs:
            print("\n❌ No PDF files found in ./pdf directory")
            print("\n💡 Add PDF files to ./pdf directory and run again")
            return
        
        print(f"\n📚 Found {len(pdfs)} PDF file(s):\n")
        for pdf_info in pdfs:
            status = "✅ Converted" if pdf_info['is_converted'] else "❌ Not converted"
            needs_update = " (needs update)" if pdf_info['needs_update'] else ""
            
            print(f"  📄 {pdf_info['pdf_name']}")
            print(f"     Status: {status}{needs_update}")
            print(f"     Output: {pdf_info['text_path'] or 'N/A'}")
            print(f"     Cache: {'✓' if pdf_info['cache_exists'] else '✗'} | Hash: {'✓' if pdf_info['hash_exists'] else '✗'}")
            print()
        
    except Exception as e:
        logger.error(f"Error listing PDFs: {e}")

def manage_documents_mode():
    """Interactive document management."""
    try:
        from manage_docs import main as manage_main
        manage_main()
    except Exception as e:
        logger.error(f"Document management error: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sortify RAG System - Study Document Q&A",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start.py --mode terminal          # Start Q&A terminal
  python start.py --mode api               # Start API server
  python start.py --list-pdfs              # List PDF conversion status
  python start.py --force-convert          # Force reconvert all PDFs
  python start.py --manage-docs            # Manage documents interactively
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['terminal', 'api'],
        default='terminal',
        help='Operation mode (default: terminal)'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='API server host (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='API server port (default: 8000)'
    )
    parser.add_argument(
        '--list-pdfs',
        action='store_true',
        help='List all PDFs and their conversion status'
    )
    parser.add_argument(
        '--force-convert',
        action='store_true',
        help='Force reconversion of all PDFs'
    )
    parser.add_argument(
        '--manage-docs',
        action='store_true',
        help='Open interactive document manager'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle special modes first
    if args.list_pdfs:
        list_pdfs()
        return
    
    if args.manage_docs:
        manage_documents_mode()
        return
    
    # Normal startup
    print_banner()
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed. Please fix issues and try again.")
        sys.exit(1)
    
    # Convert PDFs
    pdf_stats = convert_pdfs_to_text(force=args.force_convert)
    
    # Show conversion results
    if args.force_convert and pdf_stats['converted'] > 0:
        print(f"\n✅ Force converted {pdf_stats['converted']} PDF(s)")
    
    # Initialize RAG system
    rag = initialize_rag_system()
    if not rag:
        logger.error("Failed to initialize RAG system")
        sys.exit(1)
    
    # Start requested mode
    if args.mode == 'terminal':
        start_terminal_mode(rag)
    elif args.mode == 'api':
        start_api_mode(host=args.host, port=args.port)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("\n👋 Thank you for using Sortify RAG! Happy studying! 📚\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
