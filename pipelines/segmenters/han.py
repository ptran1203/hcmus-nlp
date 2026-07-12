"""Han (Literary/Classical Chinese) sentence segmenter."""
import re

from .base import SentenceSegmenter

_SENTENCE_END_RE = re.compile(r"([^。！？]*[。！？])")


class HanPunctuationSegmenter(SentenceSegmenter):
    """Splits on full-width sentence-final punctuation (。！？).

    The source texts are already densely punctuated (transcribed/annotated
    editions), so a rule-based split is sufficient without a model like HanLP.
    """

    def segment(self, text: str) -> list[str]:
        sentences = _SENTENCE_END_RE.findall(text)
        remainder = _SENTENCE_END_RE.sub("", text).strip()
        if remainder:
            sentences.append(remainder)
        return [s.strip() for s in sentences if s.strip()]
