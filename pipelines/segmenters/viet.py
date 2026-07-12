"""Vietnamese sentence segmenter."""
from .base import SentenceSegmenter


class UndertheseaSegmenter(SentenceSegmenter):
    def segment(self, text: str) -> list[str]:
        from underthesea import sent_tokenize  # lazy import: only needed if used

        return [s.strip() for s in sent_tokenize(text) if s.strip()]
