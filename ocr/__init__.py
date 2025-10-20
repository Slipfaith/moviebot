"""OCR utilities for MovieBot."""

from .processor import PosterOCR, get_default_ocr
from .local_client import LocalOCRClient

__all__ = ["PosterOCR", "get_default_ocr", "LocalOCRClient"]
