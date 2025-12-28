# data/processors/__init__.py
import sys
from pathlib import Path

# This ensures the current directory is in the path for relative imports
sys.path.append(str(Path(__file__).parent))

from processors.csv_processor import CSVProcessor
from processors.email_processor import EmailProcessor
from processors.pdf_processor import PDFProcessor

__all__ = ['CSVProcessor', 'EmailProcessor', 'PDFProcessor']