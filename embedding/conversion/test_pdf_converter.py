#!/usr/bin/env python3
"""
Unit tests for the PDFConverter class.
"""

import unittest
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Import the script to be tested
# Make sure your original script is saved as 'pdf_converter.py'
try:
    import pdf_converter
    from pdf_converter import PDFConverter
except ImportError:
    print("Error: Make sure your original script is saved as 'pdf_converter.py' in the same directory.")
    exit(1)

class TestPDFConverter(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory structure for each test."""
        # Create a top-level temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        
        # Define paths for pdfs, cache, and output
        self.pdf_dir = temp_path / "pdf_files"
        self.cache_dir = temp_path / "cache"
        self.output_dir = temp_path / "docs"
        
        # We only create the parent directories; the converter should create the final ones
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the converter
        self.converter = PDFConverter(
            pdf_dir=str(self.pdf_dir),
            cache_dir=str(self.cache_dir),
            output_dir=str(self.output_dir)
        )

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        self.temp_dir.cleanup()

    def _create_dummy_file(self, file_path: Path, content_bytes: bytes):
        """Helper function to create a dummy file with binary content."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(content_bytes)
        return file_path
    
    def _get_file_hash(self, content_bytes: bytes) -> str:
        """Helper function to get a hash of binary content."""
        return hashlib.md5(content_bytes).hexdigest()

    def test_init_creates_directories(self):
        """Test if directories are created on initialization."""
        self.assertTrue(self.pdf_dir.exists())
        self.assertTrue(self.cache_dir.exists())
        self.assertTrue(self.output_dir.exists())

    def test_get_pdf_hash(self):
        """Test the MD5 hash generation."""
        content = b"This is dummy PDF content"
        known_hash = self._get_file_hash(content)
        pdf_path = self._create_dummy_file(self.pdf_dir / "test.pdf", content)
        
        calculated_hash = self.converter._get_pdf_hash(pdf_path)
        self.assertEqual(calculated_hash, known_hash)

    def test_save_pdf_hash(self):
        """Test saving the hash file to the cache."""
        content = b"content"
        pdf_path = self._create_dummy_file(self.pdf_dir / "doc1.pdf", content)
        hash_file = self.cache_dir / "doc1.hash"
        
        self.assertFalse(hash_file.exists())
        self.converter._save_pdf_hash(pdf_path)
        self.assertTrue(hash_file.exists())
        
        with open(hash_file, 'r') as f:
            saved_hash = f.read()
        self.assertEqual(saved_hash, self._get_file_hash(content))

    def test_is_pdf_changed_no_text_file(self):
        """Test _is_pdf_changed returns True if the output text file is missing."""
        pdf_path = self._create_dummy_file(self.pdf_dir / "test.pdf", b"content")
        text_path = self.output_dir / "test.txt"
        
        # Ensure no text file exists
        self.assertFalse(text_path.exists())
        self.assertTrue(self.converter._is_pdf_changed(pdf_path, text_path))

    def test_is_pdf_changed_no_hash_file(self):
        """Test _is_pdf_changed returns True if the hash file is missing."""
        pdf_path = self._create_dummy_file(self.pdf_dir / "test.pdf", b"content")
        text_path = self.output_dir / "test.txt"
        text_path.touch() # Create empty text file
        
        # Ensure no hash file exists
        self.assertFalse((self.cache_dir / "test.hash").exists())
        self.assertTrue(self.converter._is_pdf_changed(pdf_path, text_path))

    def test_is_pdf_changed_hashes_match(self):
        """Test _is_pdf_changed returns False if hashes match."""
        content = b"content"
        pdf_path = self._create_dummy_file(self.pdf_dir / "test.pdf", content)
        text_path = self.output_dir / "test.txt"
        text_path.touch()
        
        # Create matching hash file
        self.converter._save_pdf_hash(pdf_path)
        
        self.assertFalse(self.converter._is_pdf_changed(pdf_path, text_path))

    def test_is_pdf_changed_hashes_mismatch(self):
        """Test _is_pdf_changed returns True if hashes mismatch (PDF was updated)."""
        pdf_path = self._create_dummy_file(self.pdf_dir / "test.pdf", b"old_content")
        text_path = self.output_dir / "test.txt"
        text_path.touch()
        
        # Save hash for "old_content"
        self.converter._save_pdf_hash(pdf_path)
        
        # Update PDF file with "new_content"
        self._create_dummy_file(pdf_path, b"new_content")
        
        self.assertTrue(self.converter._is_pdf_changed(pdf_path, text_path))

    def test_verify_output_exists(self):
        """Test the verification of all output files."""
        pdf_path = self.pdf_dir / "test.pdf"
        
        # 1. False: Nothing exists
        self.assertFalse(self.converter._verify_output_exists(pdf_path))
        
        # 2. False: Only one file exists
        (self.output_dir / "test.txt").touch()
        self.assertFalse(self.converter._verify_output_exists(pdf_path))
        
        # 3. True: All three files exist
        (self.output_dir / "test.txt").touch()
        (self.cache_dir / "test.txt").touch()
        (self.cache_dir / "test.hash").touch()
        self.assertTrue(self.converter._verify_output_exists(pdf_path))

    @patch('pdf_converter.PDF_SUPPORT', False)
    def test_convert_pdf_no_pypdf_support(self):
        """Test conversion failure when PDF_SUPPORT is False."""
        # Re-init converter with PDF_SUPPORT = False
        converter = PDFConverter(str(self.pdf_dir), str(self.cache_dir), str(self.output_dir))
        pdf_path = self._create_dummy_file(self.pdf_dir / "test.pdf", b"content")
        
        result = converter.convert_pdf(pdf_path)
        self.assertIsNone(result)

    def test_convert_pdf_file_not_found(self):
        """Test conversion failure when PDF file is missing."""
        pdf_path = self.pdf_dir / "non_existent.pdf"
        result = self.converter.convert_pdf(pdf_path)
        self.assertIsNone(result)

    @patch('pdf_converter.PdfReader')
    def test_convert_pdf_successful(self, mock_pdf_reader):
        """Test a successful PDF-to-text conversion."""
        # --- Setup Mock ---
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "This is page 1."
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "This is page 2."
        
        mock_reader_instance = mock_pdf_reader.return_value
        mock_reader_instance.pages = [mock_page1, mock_page2]
        
        # --- Create Dummy PDF ---
        content = b"dummy pdf data"
        pdf_path = self._create_dummy_file(self.pdf_dir / "test.pdf", content)
        
        # --- Run Conversion ---
        result_path = self.converter.convert_pdf(pdf_path)
        
        # --- Verify Paths ---
        expected_text_path = self.output_dir / "test.txt"
        expected_cache_path = self.cache_dir / "test.txt"
        expected_hash_path = self.cache_dir / "test.hash"
        
        self.assertEqual(result_path, expected_text_path)
        
        # --- Verify Mock ---
        mock_pdf_reader.assert_called_once_with(pdf_path)
        
        # --- Verify Content ---
        expected_content = "This is page 1.\n\nThis is page 2."
        with open(result_path, 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), expected_content)
        
        # Verify cache text file has same content
        with open(expected_cache_path, 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), expected_content)
        
        # --- Verify Hash ---
        self.assertTrue(expected_hash_path.exists())
        with open(expected_hash_path, 'r') as f:
            self.assertEqual(f.read(), self._get_file_hash(content))

    @patch('pdf_converter.PdfReader')
    def test_convert_pdf_skip_unchanged(self, mock_pdf_reader):
        """Test that an unchanged file is skipped and PdfReader is not called."""
        pdf_path = self._create_dummy_file(self.pdf_dir / "test.pdf", b"content")
        text_path = self.output_dir / "test.txt"
        
        # Simulate a previous conversion
        text_path.touch()
        self.converter._save_pdf_hash(pdf_path)
        
        # Run conversion
        result = self.converter.convert_pdf(pdf_path, force=False)
        
        # Assert
        self.assertEqual(result, text_path)
        mock_pdf_reader.assert_not_called() # The key assertion

    @patch('pdf_converter.PdfReader')
    def test_convert_pdf_force_conversion(self, mock_pdf_reader):
        """Test that 'force=True' re-converts an unchanged file."""
        # --- Setup Mock ---
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "forced text"
        mock_reader_instance = mock_pdf_reader.return_value
        mock_reader_instance.pages = [mock_page]
        
        pdf_path = self._create_dummy_file(self.pdf_dir / "test.pdf", b"content")
        text_path = self.output_dir / "test.txt"
        
        # Simulate a previous conversion
        text_path.write_text("old text")
        self.converter._save_pdf_hash(pdf_path)
        
        # Run conversion with force=True
        result = self.converter.convert_pdf(pdf_path, force=True)
        
        # Assert
        self.assertEqual(result, text_path)
        mock_pdf_reader.assert_called_once() # Should be called
        with open(text_path, 'r') as f:
            self.assertEqual(f.read(), "forced text") # Content is updated

    @patch('pdf_converter.PdfReader')
    def test_convert_pdf_no_text_extracted(self, mock_pdf_reader):
        """Test a PDF that returns no text (e.g., image-only PDF)."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "" # Empty text
        mock_reader_instance = mock_pdf_reader.return_value
        mock_reader_instance.pages = [mock_page]
        
        pdf_path = self._create_dummy_file(self.pdf_dir / "empty.pdf", b"data")
        
        result = self.converter.convert_pdf(pdf_path)
        self.assertIsNone(result) # Should fail conversion
        self.assertFalse((self.output_dir / "empty.txt").exists())

    @patch('pdf_converter.PdfReader')
    def test_convert_pdf_extraction_error(self, mock_pdf_reader):
        """Test a PDF where a page fails to extract."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1"
        mock_page2 = MagicMock()
        mock_page2.extract_text.side_effect = Exception("Mocked extraction error")
        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = "Page 3"
        
        mock_reader_instance = mock_pdf_reader.return_value
        mock_reader_instance.pages = [mock_page1, mock_page2, mock_page3]

        pdf_path = self._create_dummy_file(self.pdf_dir / "partial.pdf", b"data")
        result_path = self.converter.convert_pdf(pdf_path)
        
        # Should still succeed but only with text from pages 1 and 3
        self.assertIsNotNone(result_path)
        with open(result_path, 'r') as f:
            content = f.read()
            self.assertIn("Page 1", content)
            self.assertNotIn("Page 2", content)
            self.assertIn("Page 3", content)
            self.assertEqual(content, "Page 1\n\nPage 3")

    @patch('pdf_converter.PdfReader')
    def test_convert_all_pdfs_flow(self, mock_pdf_reader):
        """Test converting a directory of multiple PDFs."""
        # --- Setup Mocks ---
        # Mock PdfReader to return different text based on the file it's called with
        def pdf_reader_side_effect(path):
            mock_reader = MagicMock()
            if path.stem == 'doc1':
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "Doc 1 Text"
                mock_reader.pages = [mock_page]
            elif path.stem == 'doc3':
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "Doc 3 Text"
                mock_reader.pages = [mock_page]
            elif path.stem == 'doc4-fail':
                mock_reader.pages = [] # No pages, will cause "no text" warning
            return mock_reader
        
        mock_pdf_reader.side_effect = pdf_reader_side_effect

        # --- Create Dummy Files ---
        pdf1_path = self._create_dummy_file(self.pdf_dir / "doc1.pdf", b"doc1")
        pdf2_path = self._create_dummy_file(self.pdf_dir / "doc2.pdf", b"doc2")
        pdf3_path = self._create_dummy_file(self.pdf_dir / "doc3.pdf", b"doc3")
        pdf4_path = self._create_dummy_file(self.pdf_dir / "doc4-fail.pdf", b"doc4")
        
        # Simulate doc2 is already converted and unchanged
        (self.output_dir / "doc2.txt").touch()
        self.converter._save_pdf_hash(pdf2_path)
        
        # --- Run Conversion ---
        stats = self.converter.convert_all_pdfs()

        # --- Assertions ---
        self.assertEqual(stats['total'], 4)
        self.assertEqual(stats['converted'], 2) # doc1 and doc3
        self.assertEqual(stats['skipped'], 1)   # doc2
        self.assertEqual(stats['failed'], 1)    # doc4-fail
        
        # Check that PdfReader was called for the correct files
        mock_pdf_reader.assert_has_calls([
            call(pdf1_path),
            call(pdf3_path),
            call(pdf4_path)
        ], any_order=True)
        self.assertEqual(mock_pdf_reader.call_count, 3) # Not called for doc2

    def test_clean_orphaned_files(self):
        """Test that orphaned cache/output files are removed."""
        # Create a "valid" file set
        pdf_path = self._create_dummy_file(self.pdf_dir / "keep.pdf", b"keep")
        self.converter._save_pdf_hash(pdf_path)
        (self.output_dir / "keep.txt").touch()
        (self.cache_dir / "keep.txt").touch()
        
        # Create "orphaned" file set (no matching .pdf)
        (self.cache_dir / "orphan.hash").touch()
        (self.cache_dir / "orphan.txt").touch()
        (self.output_dir / "orphan.txt").touch()
        
        # Run cleanup
        self.converter.clean_orphaned_files()
        
        # Assert valid files remain
        self.assertTrue((self.output_dir / "keep.txt").exists())
        self.assertTrue((self.cache_dir / "keep.hash").exists())
        self.assertTrue((self.cache_dir / "keep.txt").exists())
        
        # Assert orphaned files are gone
        self.assertFalse((self.output_dir / "orphan.txt").exists())
        self.assertFalse((self.cache_dir / "orphan.hash").exists())
        self.assertFalse((self.cache_dir / "orphan.txt").exists())

    def test_list_pdfs(self):
        """Test the listing and status reporting of PDFs."""
        # PDF 1: Converted and up-to-date
        pdf1_path = self._create_dummy_file(self.pdf_dir / "doc1.pdf", b"doc1")
        self.converter._save_pdf_hash(pdf1_path)
        (self.output_dir / "doc1.txt").touch()
        (self.cache_dir / "doc1.txt").touch()
        
        # PDF 2: Not yet converted
        pdf2_path = self._create_dummy_file(self.pdf_dir / "doc2.pdf", b"doc2")
        
        # PDF 3: Converted but PDF has changed (needs update)
        pdf3_path = self._create_dummy_file(self.pdf_dir / "doc3.pdf", b"doc3_old")
        self.converter._save_pdf_hash(pdf3_path)
        (self.output_dir / "doc3.txt").touch()
        (self.cache_dir / "doc3.txt").touch()
        # Now, "update" the PDF
        self._create_dummy_file(self.pdf_dir / "doc3.pdf", b"doc3_new")
        
        # Get list
        pdf_list = {p['pdf_name']: p for p in self.converter.list_pdfs()}
        
        self.assertEqual(len(pdf_list), 3)
        
        # Check doc1
        self.assertTrue(pdf_list['doc1.pdf']['is_converted'])
        self.assertFalse(pdf_list['doc1.pdf']['needs_update'])
        
        # Check doc2
        self.assertFalse(pdf_list['doc2.pdf']['is_converted'])
        self.assertTrue(pdf_list['doc2.pdf']['needs_update'])
        
        # Check doc3
        self.assertTrue(pdf_list['doc3.pdf']['is_converted']) # Output exists
        self.assertTrue(pdf_list['doc3.pdf']['needs_update']) # Hash mismatch


if __name__ == '__main__':
    # This assumes your main script (pdf_converter.py) has PDF_SUPPORT = True
    # or that pypdf is installed.
    if not pdf_converter.PDF_SUPPORT:
        print("\nWARNING: 'pypdf' not installed. Skipping tests that require it.")
        print("To run all tests, please install pypdf: pip install pypdf\n")
    
    unittest.main(verbosity=2)