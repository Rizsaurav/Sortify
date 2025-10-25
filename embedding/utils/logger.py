import logging
import sys
from typing import Optional
from pathlib import Path

class LoggerFactory:
    """Factory for creating configured loggers."""
    
    _configured = False
    
    @classmethod
    def configure(cls, level: str = "INFO", log_file: Optional[str] = None):
        """Configure global logging settings."""
        if cls._configured:
            return
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (optional)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        cls._configured = True
        
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance with the given name."""
        if not cls._configured:
            cls.configure()
        return logging.getLogger(name)