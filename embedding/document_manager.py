#!/usr/bin/env python3
"""Minimal document manager."""
from pathlib import Path
from typing import List
from fastapi import UploadFile
import shutil

class DocumentManager:
    def __init__(self, documents_dir: str):
        self.documents_dir = Path(documents_dir)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
    
    def save_uploaded_file(self, file: UploadFile) -> Path:
        """Save uploaded file."""
        filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_")
        file_path = self.documents_dir / filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return file_path
    
    def list_documents(self) -> List[str]:
        """List all .txt files."""
        return [f.name for f in self.documents_dir.glob("*.txt")]
    
    def delete_document(self, filename: str) -> bool:
        """Delete a document."""
        file_path = self.documents_dir / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False

