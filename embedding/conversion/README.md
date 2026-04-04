# PDF Conversion Module

## Overview

This module provides PDF to text conversion functionality for the Sortify RAG system. It automatically detects, converts, and caches PDF files, making their content available for embedding and question-answering.

## Features

- **Automatic Detection**: Scans `pdf/` directory for PDF files
- **Smart Caching**: Only converts new or modified PDFs (uses MD5 hashing)
- **Error Handling**: Gracefully handles corrupted or problematic PDFs
- **Progress Logging**: Clear status indicators for conversion progress
- **API Integration**: Supports PDF uploads through FastAPI endpoints

## Module Structure

```
conversion/
├── __init__.py           # Package initialization
├── pdf_converter.py      # Core PDF conversion logic
└── README.md            # This file
```

## Usage

### As a Module

```python
from conversion.pdf_converter import PDFConverter

# Initialize converter
converter = PDFConverter(
    pdf_dir="./pdf",              # Input directory
    cache_dir="./storage/pdf_cache",  # Cache directory
    output_dir="./docs"           # Output directory
)

# Convert all PDFs
stats = converter.convert_all_pdfs()
print(f"Converted: {stats['converted']}, Skipped: {stats['skipped']}")

# Convert specific PDF
from pathlib import Path
pdf_path = Path("./pdf/document.pdf")
text_path = converter.convert_pdf(pdf_path)

# List all PDFs with status
pdfs = converter.list_pdfs()
for pdf in pdfs:
    print(f"{pdf['pdf_name']}: {'✅' if pdf['is_converted'] else '❌'}")
```

### Standalone Script

```bash
# Convert all PDFs
python -m conversion.pdf_converter

# List PDFs
python -m conversion.pdf_converter --list

# Force reconversion
python -m conversion.pdf_converter --force

# Convert specific file
python -m conversion.pdf_converter --file path/to/document.pdf
```

## API Reference

### PDFConverter Class

#### `__init__(pdf_dir, cache_dir, output_dir)`

Initialize the PDF converter.

**Parameters:**
- `pdf_dir` (str): Directory containing PDF files
- `cache_dir` (str): Directory for caching conversions
- `output_dir` (str): Directory for output text files

#### `convert_pdf(pdf_path, force=False)`

Convert a single PDF file to text.

**Parameters:**
- `pdf_path` (Path): Path to PDF file
- `force` (bool): Force conversion even if unchanged

**Returns:**
- Path to converted text file, or None if failed

#### `convert_all_pdfs(force=False)`

Convert all PDF files in the PDF directory.

**Parameters:**
- `force` (bool): Force conversion of all PDFs

**Returns:**
- Dictionary with conversion statistics:
  ```python
  {
      'total': int,      # Total PDFs found
      'converted': int,  # PDFs converted
      'skipped': int,    # PDFs skipped (unchanged)
      'failed': int,     # PDFs that failed
      'files': [...]     # List of file details
  }
  ```

#### `list_pdfs()`

List all PDF files with their conversion status.

**Returns:**
- List of dictionaries with PDF information:
  ```python
  [{
      'pdf_name': str,        # PDF filename
      'pdf_path': str,        # Full path to PDF
      'text_exists': bool,    # Text file exists
      'text_path': str,       # Path to text file (if exists)
      'is_converted': bool,   # Has been converted
      'needs_update': bool    # PDF changed since conversion
  }, ...]
  ```

## Caching Mechanism

The module uses MD5 hashing to track file changes:

1. **First Conversion**: Converts PDF and saves hash
2. **Subsequent Runs**: Compares current hash with cached hash
3. **If Changed**: Reconverts PDF
4. **If Unchanged**: Skips conversion

Cache structure:
```
storage/pdf_cache/
├── document.txt      # Cached text content
├── document.hash     # MD5 hash of PDF
├── resume.txt
└── resume.hash
```

## Error Handling

The module handles various error scenarios:

### Missing pypdf Library
```python
# Falls back gracefully
if not PDF_SUPPORT:
    logger.warning("pypdf not installed")
    # Continue with existing text files
```

### Corrupted PDF
```python
# Logs error and continues
try:
    reader = PdfReader(pdf_path)
except Exception as e:
    logger.error(f"Error converting {pdf_path}: {e}")
    return None
```

### Empty PDF
```python
# Warns but doesn't create file
if not full_text.strip():
    logger.warning(f"No text extracted from {pdf_path}")
    return None
```

## Dependencies

- `pypdf` (>= 5.0.0): PDF reading and text extraction
- `hashlib` (stdlib): File change detection
- `pathlib` (stdlib): Path operations
- `logging` (stdlib): Progress logging

Install dependencies:
```bash
pip install pypdf
```

## Integration Points

### 1. start.py

Automatically converts PDFs on startup:

```python
from conversion.pdf_converter import PDFConverter

def convert_pdfs_to_text():
    converter = PDFConverter(...)
    stats = converter.convert_all_pdfs()
    logger.info(f"Converted {stats['converted']} PDFs")
```

### 2. api_service.py

Handles PDF uploads via API:

```python
async def upload_document(file: UploadFile):
    if file.filename.endswith('.pdf'):
        # Save and convert PDF
        pdf_path = save_pdf(file)
        text_path = converter.convert_pdf(pdf_path)
```

### 3. rag_system.py

Processes converted text files:

```python
# Text files from converted PDFs are automatically processed
rag.load_documents("*.txt")  # Includes converted PDFs
```

## Performance

### Conversion Speed

| PDF Size | Pages | Time |
|----------|-------|------|
| Small    | 1-10  | < 1s |
| Medium   | 10-100 | 1-5s |
| Large    | 100+  | 5-30s |

### Optimization

- **Parallel Processing**: Future enhancement for batch conversion
- **Incremental Updates**: Only converts changed files
- **Efficient Hashing**: MD5 for fast change detection

## Limitations

Current limitations:

1. **Image-based PDFs**: Cannot extract text from scanned images
2. **Protected PDFs**: Password-protected PDFs not supported
3. **Complex Layouts**: Tables and figures may not extract perfectly
4. **Encoding Issues**: Some special characters may not convert correctly

## Future Enhancements

Planned improvements:

- [ ] OCR support for scanned PDFs
- [ ] Parallel PDF conversion
- [ ] Support for other formats (DOCX, PPTX)
- [ ] Table extraction and formatting
- [ ] Metadata extraction (author, title, etc.)
- [ ] Image extraction and description
- [ ] Multi-language support

## Troubleshooting

### No text extracted

**Problem**: `logger.warning("No text extracted from X.pdf")`

**Solutions:**
1. Check if PDF is image-based (needs OCR)
2. Try opening PDF in a reader
3. Re-save PDF to fix corruption

### Import error

**Problem**: `ModuleNotFoundError: No module named 'pypdf'`

**Solution:**
```bash
pip install pypdf
```

### Permission errors

**Problem**: Cannot write to cache/output directories

**Solution:**
```bash
# Ensure directories are writable
chmod 755 storage/pdf_cache docs
```

## Testing

Run tests:

```bash
# Test conversion
python -m pytest tests/test_pdf_converter.py

# Manual test
python convert_pdfs.py --list
python convert_pdfs.py
```

## Contributing

To add new features:

1. Add methods to `PDFConverter` class
2. Update `main()` function for CLI
3. Add error handling
4. Update documentation
5. Add tests

## License

Part of the Sortify RAG system.
