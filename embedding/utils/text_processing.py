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
    
    @classmethod
    def compute_hash(cls, text: str) -> str:
        """
        Compute SHA-256 hash of text.
        
        Args:
            text: Text to hash
        
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    @classmethod
    def split_into_sentences(cls, text: str) -> List[str]:
        """
        Split text into sentences intelligently.
        
        Args:
            text: Text to split
        
        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with NLTK/spaCy if needed)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]