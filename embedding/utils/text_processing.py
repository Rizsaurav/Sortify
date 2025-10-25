import re
import hashlib
from typing import List

class TextProcessor:
    """Text processing utilities."""
    
    # Compiled regex patterns for efficiency
    URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PDF_ARTIFACTS = re.compile(r'(\x00|\ufffd|\.{3,}|\s{3,})')
    MULTIPLE_NEWLINES = re.compile(r'\n{3,}')
    MULTIPLE_SPACES = re.compile(r' {2,}')
    
    @classmethod
    def clean_text(cls, text: str, remove_urls: bool = True, remove_emails: bool = True) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Raw text to clean
            remove_urls: Whether to remove URLs
            remove_emails: Whether to remove email addresses
        
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove URLs
        if remove_urls:
            text = cls.URL_PATTERN.sub(' ', text)
        
        # Remove emails
        if remove_emails:
            text = cls.EMAIL_PATTERN.sub(' ', text)
        
        # Remove PDF artifacts
        text = cls.PDF_ARTIFACTS.sub(' ', text)
        
        # Normalize whitespace
        text = cls.MULTIPLE_NEWLINES.sub('\n\n', text)
        text = cls.MULTIPLE_SPACES.sub(' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text