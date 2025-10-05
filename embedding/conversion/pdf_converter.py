#!/usr/bin/env python3
"""
PDF to text conversion utility for the RAG system.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
import hashlib

try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("pypdf not installed. PDF support disabled. Install with: pip install pypdf")

logger = logging.getLogger(__name__)

class PDFConverter:
    """Convert PDF files to text and cache the results."""
    
    def __init__(self, pdf_dir: str = "./pdf", cache_dir: str = "./storage/pdf_cache", output_dir: str = "./docs"):
        """
        Initialize PDF converter.
        
        Args:
            pdf_dir: Directory containing PDF files
            cache_dir: Directory to cache extracted text (for tracking changes)
            output_dir: Directory to output converted text files
        """
        self.pdf_dir = Path(pdf_dir)
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        
        # Create directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not PDF_SUPPORT:
            logger.warning("PDF support is not available")
    
    def _get_pdf_hash(self, pdf_path: Path) -> str:
        """Get hash of PDF file for change detection."""
        hash_md5 = hashlib.md5()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _is_pdf_changed(self, pdf_path: Path, text_path: Path) -> bool:
        """Check if PDF has changed since last conversion."""
        hash_file = self.cache_dir / f"{pdf_path.stem}.hash"
        
        # If text file doesn't exist, PDF needs conversion
        if not text_path.exists():
            return True
        
        # If hash file doesn't exist, PDF needs conversion
        if not hash_file.exists():
            return True
        
        # Compare current hash with cached hash
        current_hash = self._get_pdf_hash(pdf_path)
        with open(hash_file, 'r') as f:
            cached_hash = f.read().strip()
        
        return current_hash != cached_hash
    
    def _save_pdf_hash(self, pdf_path: Path):
        """Save hash of PDF file for change detection."""
        hash_file = self.cache_dir / f"{pdf_path.stem}.hash"
        current_hash = self._get_pdf_hash(pdf_path)
        with open(hash_file, 'w') as f:
            f.write(current_hash)
    
    def convert_pdf(self, pdf_path: Path, force: bool = False) -> Optional[Path]:
        """
        Convert a single PDF file to text.
        
        Args:
            pdf_path: Path to PDF file
            force: Force conversion even if file hasn't changed
            
        Returns:
            Path to converted text file, or None if conversion failed
        """
        if not PDF_SUPPORT:
            logger.error("PDF support not available. Install pypdf: pip install pypdf")
            return None
        
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        
        # Output text file path
        text_filename = f"{pdf_path.stem}.txt"
        text_path = self.output_dir / text_filename
        
        # Check if conversion is needed
        if not force and not self._is_pdf_changed(pdf_path, text_path):
            logger.info(f"📄 {pdf_path.name} -> {text_filename} (unchanged, skipping)")
            return text_path
        
        try:
            # Read PDF
            logger.info(f"🔄 Converting {pdf_path.name}...")
            reader = PdfReader(pdf_path)
            
            # Extract text from all pages
            text_content = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
            
            # Combine all pages
            full_text = "\n\n".join(text_content)
            
            if not full_text.strip():
                logger.warning(f"⚠️  No text extracted from {pdf_path.name}")
                return None
            
            # Save to output directory
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            # Also save to cache directory for tracking
            cache_text_path = self.cache_dir / text_filename
            with open(cache_text_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            # Save hash for change detection
            self._save_pdf_hash(pdf_path)
            
            word_count = len(full_text.split())
            logger.info(f"✅ {pdf_path.name} -> {text_filename} ({len(reader.pages)} pages, {word_count} words)")
            
            return text_path
            
        except Exception as e:
            logger.error(f"❌ Error converting {pdf_path.name}: {e}")
            return None
    
    def convert_all_pdfs(self, force: bool = False) -> Dict[str, any]:
        """
        Convert all PDF files in the PDF directory.
        
        Args:
            force: Force conversion of all PDFs even if unchanged
            
        Returns:
            Dictionary with conversion statistics
        """
        if not PDF_SUPPORT:
            logger.error("PDF support not available. Install with: pip install pypdf")
            return {
                'total': 0,
                'converted': 0,
                'skipped': 0,
                'failed': 0,
                'error': 'pypdf not installed'
            }
        
        if not self.pdf_dir.exists():
            logger.warning(f"PDF directory not found: {self.pdf_dir}")
            return {
                'total': 0,
                'converted': 0,
                'skipped': 0,
                'failed': 0
            }
        
        # Find all PDF files
        pdf_files = list(self.pdf_dir.glob("*.pdf")) + list(self.pdf_dir.glob("*.PDF"))
        
        if not pdf_files:
            logger.info(f"No PDF files found in {self.pdf_dir}")
            return {
                'total': 0,
                'converted': 0,
                'skipped': 0,
                'failed': 0
            }
        
        logger.info(f"📚 Found {len(pdf_files)} PDF file(s)")
        
        stats = {
            'total': len(pdf_files),
            'converted': 0,
            'skipped': 0,
            'failed': 0,
            'files': []
        }
        
        for pdf_path in pdf_files:
            text_path = self.output_dir / f"{pdf_path.stem}.txt"
            
            # Check if needs conversion
            if not force and not self._is_pdf_changed(pdf_path, text_path):
                stats['skipped'] += 1
                stats['files'].append({
                    'name': pdf_path.name,
                    'status': 'skipped',
                    'output': str(text_path)
                })
                logger.info(f"⏭️  {pdf_path.name} (unchanged)")
                continue
            
            # Convert PDF
            result_path = self.convert_pdf(pdf_path, force=force)
            
            if result_path:
                stats['converted'] += 1
                stats['files'].append({
                    'name': pdf_path.name,
                    'status': 'converted',
                    'output': str(result_path)
                })
            else:
                stats['failed'] += 1
                stats['files'].append({
                    'name': pdf_path.name,
                    'status': 'failed',
                    'output': None
                })
        
        return stats
    
    def list_pdfs(self) -> List[Dict[str, any]]:
        """List all PDF files with their conversion status."""
        if not self.pdf_dir.exists():
            return []
        
        pdf_files = list(self.pdf_dir.glob("*.pdf")) + list(self.pdf_dir.glob("*.PDF"))
        
        result = []
        for pdf_path in pdf_files:
            text_path = self.output_dir / f"{pdf_path.stem}.txt"
            cache_path = self.cache_dir / f"{pdf_path.stem}.txt"
            
            result.append({
                'pdf_name': pdf_path.name,
                'pdf_path': str(pdf_path),
                'text_exists': text_path.exists(),
                'text_path': str(text_path) if text_path.exists() else None,
                'is_converted': cache_path.exists(),
                'needs_update': self._is_pdf_changed(pdf_path, text_path) if PDF_SUPPORT else False
            })
        
        return result


def main():
    """Command-line interface for PDF conversion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert PDF files to text for RAG system")
    parser.add_argument('--pdf-dir', default='./pdf', help='Directory containing PDF files')
    parser.add_argument('--output-dir', default='./docs', help='Output directory for text files')
    parser.add_argument('--cache-dir', default='./storage/pdf_cache', help='Cache directory for tracking changes')
    parser.add_argument('--force', action='store_true', help='Force conversion of all PDFs')
    parser.add_argument('--list', action='store_true', help='List all PDFs and their status')
    parser.add_argument('--file', type=str, help='Convert a specific PDF file')
    
    args = parser.parse_args()
    
    converter = PDFConverter(
        pdf_dir=args.pdf_dir,
        cache_dir=args.cache_dir,
        output_dir=args.output_dir
    )
    
    if args.list:
        pdfs = converter.list_pdfs()
        if not pdfs:
            print("No PDF files found")
        else:
            print(f"\n📚 Found {len(pdfs)} PDF file(s):\n")
            for pdf_info in pdfs:
                status = "✅ Converted" if pdf_info['is_converted'] else "❌ Not converted"
                needs_update = " (needs update)" if pdf_info['needs_update'] else ""
                print(f"  {pdf_info['pdf_name']}: {status}{needs_update}")
                if pdf_info['text_path']:
                    print(f"    → {pdf_info['text_path']}")
    
    elif args.file:
        pdf_path = Path(args.file)
        result = converter.convert_pdf(pdf_path, force=args.force)
        if result:
            print(f"✅ Converted: {result}")
        else:
            print(f"❌ Failed to convert: {pdf_path}")
    
    else:
        print("\n🔄 Converting PDF files...")
        print("=" * 50)
        stats = converter.convert_all_pdfs(force=args.force)
        
        print("\n📊 Conversion Summary:")
        print(f"  Total:     {stats['total']}")
        print(f"  Converted: {stats['converted']}")
        print(f"  Skipped:   {stats['skipped']}")
        print(f"  Failed:    {stats['failed']}")
        
        if stats['converted'] > 0:
            print(f"\n✅ Successfully converted {stats['converted']} PDF(s) to text")
            print(f"📁 Text files saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
