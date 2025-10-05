#!/usr/bin/env python3
"""
Standalone script to convert PDF files to text.
Can be run independently or used by other scripts.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from conversion.pdf_converter import PDFConverter

def main():
    """Main function to convert PDFs."""
    print("🔄 PDF to Text Converter for Sortify RAG")
    print("=" * 50)
    
    # Initialize converter with default paths
    converter = PDFConverter(
        pdf_dir="./pdf",
        cache_dir="./storage/pdf_cache",
        output_dir="./docs"
    )
    
    # List PDFs first
    pdfs = converter.list_pdfs()
    
    if not pdfs:
        print("\n❌ No PDF files found in ./pdf directory")
        print("\n💡 Tips:")
        print("  1. Place PDF files in the ./pdf directory")
        print("  2. Supported formats: .pdf, .PDF")
        print("  3. Run this script again after adding PDFs")
        return
    
    print(f"\n📚 Found {len(pdfs)} PDF file(s):\n")
    for pdf_info in pdfs:
        if pdf_info['is_converted']:
            status = "✅ Already converted"
            if pdf_info['needs_update']:
                status += " (file changed, will reconvert)"
        else:
            status = "⏳ Not yet converted"
        
        print(f"  • {pdf_info['pdf_name']}: {status}")
    
    print("\n" + "=" * 50)
    print("🔄 Starting conversion...\n")
    
    # Convert all PDFs
    stats = converter.convert_all_pdfs()
    
    print("\n" + "=" * 50)
    print("📊 Conversion Summary:")
    print(f"  Total PDFs:     {stats['total']}")
    print(f"  Converted:      {stats['converted']}")
    print(f"  Skipped:        {stats['skipped']} (unchanged)")
    print(f"  Failed:         {stats['failed']}")
    
    if stats['converted'] > 0:
        print(f"\n✅ Successfully converted {stats['converted']} PDF(s)")
        print("📁 Text files saved to: ./docs")
        print("\n💡 Next steps:")
        print("  1. Text files are now available in ./docs")
        print("  2. Run 'python start.py' to process them with the RAG system")
    elif stats['skipped'] > 0:
        print("\n✅ All PDFs are already converted and up to date")
        print("💡 To force reconversion, run: python convert_pdfs.py --force")
    
    if stats['failed'] > 0:
        print(f"\n⚠️  {stats['failed']} PDF(s) failed to convert")
        print("Please check the error messages above")
    
    print("=" * 50)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert PDF files to text")
    parser.add_argument('--force', action='store_true', help='Force reconversion of all PDFs')
    parser.add_argument('--list', action='store_true', help='Only list PDFs without converting')
    
    args = parser.parse_args()
    
    if args.list:
        # Just list PDFs
        converter = PDFConverter()
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
    else:
        main()
