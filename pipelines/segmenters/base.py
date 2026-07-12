"""Abstract sentence-segmenter interface, so the backend per language is swappable."""
from abc import ABC, abstractmethod


class SentenceSegmenter(ABC):
    @abstractmethod
    def segment(self, text: str) -> list[str]:
        """Split a paragraph into a list of sentences."""
