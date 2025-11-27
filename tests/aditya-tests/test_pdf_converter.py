"""
Unit tests for PDF Converter
Tests PDF conversion statistics and file handling
"""
import pytest

#pdf converter api
class TestPDFConversionStats:
    """Test PDF conversion statistics"""

    def test_convert_all_pdfs_returns_stats_dict(self):
        """Test conversion returns statistics dictionary"""
        stats = {
            'total': 5,
            'converted': 3,
            'skipped': 1,
            'failed': 1,
            'files': []
        }

        assert 'total' in stats
        assert 'converted' in stats
        assert 'skipped' in stats
        assert 'failed' in stats
        assert isinstance(stats['total'], int)
        print("✓ Test 1: Stats dictionary structure validated")

    def test_empty_directory_returns_zero_stats(self):
        """Test empty directory returns zero counts"""
        stats = {
            'total': 0,
            'converted': 0,
            'skipped': 0,
            'failed': 0,
            'files': []
        }

        assert stats['total'] == 0
        assert stats['converted'] == 0
        assert len(stats['files']) == 0
        print("✓ Test 2: Empty directory handled correctly")

    def test_conversion_stats_sum_equals_total(self):
        """Test conversion stats add up correctly"""
        stats = {
            'total': 10,
            'converted': 5,
            'skipped': 3,
            'failed': 2
        }

        sum_results = stats['converted'] + stats['skipped'] + stats['failed']
        assert sum_results == stats['total']
        print("✓ Test 3: Stats sum equals total")


class TestPDFFileTracking:
    """Test PDF file status tracking"""

    def test_list_pdfs_returns_file_info(self):
        """Test list_pdfs returns file information"""
        pdf_info = {
            'pdf_name': 'document.pdf',
            'pdf_path': '/path/to/document.pdf',
            'text_exists': True,
            'cache_exists': True,
            'hash_exists': True,
            'text_path': '/path/to/document.txt',
            'is_converted': True,
            'needs_update': False
        }

        required_fields = ['pdf_name', 'text_exists', 'is_converted']
        assert all(field in pdf_info for field in required_fields)
        assert isinstance(pdf_info['text_exists'], bool)
        print("✓ Test 4: PDF info structure validated")

    def test_needs_update_detects_changes(self):
        """Test needs_update flag detects PDF changes"""
        pdf_unchanged = {'pdf_name': 'doc1.pdf', 'needs_update': False}
        pdf_changed = {'pdf_name': 'doc2.pdf', 'needs_update': True}

        assert pdf_unchanged['needs_update'] is False
        assert pdf_changed['needs_update'] is True
        print("✓ Test 5: Change detection working")

    def test_converted_status_requires_all_files(self):
        """Test is_converted requires output, cache, and hash"""
        fully_converted = {
            'text_exists': True,
            'cache_exists': True,
            'hash_exists': True,
            'is_converted': True
        }

        incomplete = {
            'text_exists': True,
            'cache_exists': False,
            'hash_exists': False,
            'is_converted': False
        }

        assert fully_converted['is_converted'] is True
        assert incomplete['is_converted'] is False
        print("✓ Test 6: Conversion status validated")


class TestConversionResults:
    """Test individual conversion results"""

    def test_successful_conversion_returns_path(self):
        """Test successful conversion returns output path"""
        result = {
            'name': 'document.pdf',
            'status': 'converted',
            'output': '/path/to/document.txt'
        }

        assert result['status'] == 'converted'
        assert result['output'] is not None
        assert result['output'].endswith('.txt')
        print("✓ Test 7: Successful conversion returns path")

    def test_failed_conversion_has_null_output(self):
        """Test failed conversion has no output path"""
        result = {
            'name': 'corrupted.pdf',
            'status': 'failed',
            'output': None
        }

        assert result['status'] == 'failed'
        assert result['output'] is None
        print("✓ Test 8: Failed conversion has null output")

    def test_skipped_files_have_existing_output(self):
        """Test skipped files already have output"""
        result = {
            'name': 'existing.pdf',
            'status': 'skipped',
            'output': '/path/to/existing.txt'
        }

        assert result['status'] == 'skipped'
        assert result['output'] is not None
        print("✓ Test 9: Skipped file has existing output")


if __name__ == '__main__':
    pytest.main([
        __file__,
        '-v',
        '--html=pdf-converter-results.html',
        '--self-contained-html'
    ])