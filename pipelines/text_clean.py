"""Shared text-cleaning helpers for the Han/Viet corpus pipeline."""
import re
import unicodedata

_PAGE_NUMBER_RE = re.compile(r"^\s*[-–—]?\s*\d{1,4}\s*[-–—]?\s*$")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def dehyphenate(text: str) -> str:
    """Join words split across a line break by a hyphen (PDF line-wrap artifact)."""
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


def clean_text(text: str) -> str:
    text = normalize_unicode(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = dehyphenate(text)
    lines = [ln for ln in text.split("\n") if not _PAGE_NUMBER_RE.match(ln)]
    text = "\n".join(lines)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n")]
    return [p for p in paras if p]
