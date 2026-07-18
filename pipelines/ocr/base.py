"""Abstract OCR engine interface, so the backend is swappable."""
from abc import ABC, abstractmethod


class OCREngine(ABC):
    @abstractmethod
    def extract_text(self, image_path: str) -> str:
        """OCR a single page image file into text."""
