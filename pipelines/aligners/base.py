"""Abstract sentence-aligner interface, so the backend/model is swappable."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AlignedPair:
    han_ids: list[int]
    viet_ids: list[int]
    han_text: str
    viet_text: str
    score: float


class SentenceAligner(ABC):
    @abstractmethod
    def align(self, han_sents: list[str], viet_sents: list[str]) -> list[AlignedPair]:
        """Align two ordered sentence lists into a list of aligned spans.

        A span with an empty han_ids or viet_ids represents a sentence that
        couldn't be matched (dropped/unaligned), kept for reporting coverage.
        """
