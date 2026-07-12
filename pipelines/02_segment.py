"""Split cleaned paragraph/page-level JSONL into sentence-level JSONL.

Reads dataset/cleaned/<slug>/{han,viet}.jsonl and writes
dataset/segmented/<slug>/{han,viet}.jsonl, one row per sentence, keeping a
back-reference to the source paragraph/page for provenance.

The segmenter used per language is a one-line swap in SEGMENTERS below -- add
a new class implementing SentenceSegmenter and point the registry at it to
change backends (e.g. Underthesea -> VnCoreNLP, rule-based Han -> HanLP)
without touching the rest of this script.

Usage:
    python pipelines/02_segment.py [--only slug1,slug2]
"""
import argparse
import json
import logging
from pathlib import Path

from config import BOOKS, CLEANED_DIR
from segmenters.base import SentenceSegmenter
from segmenters.han import HanPunctuationSegmenter
from segmenters.viet import UndertheseaSegmenter

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

SEGMENTED_DIR = CLEANED_DIR.parent / "segmented"

SEGMENTERS: dict[str, SentenceSegmenter] = {
    "han": HanPunctuationSegmenter(),
    "viet": UndertheseaSegmenter(),
}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(records: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def join_paragraphs(paragraphs: list[dict]) -> tuple[str, list[tuple]]:
    """Concatenate paragraphs into one string so sentences aren't cut at
    page/paragraph boundaries, keeping (start, end, page, para_id) spans to
    trace each sentence back to its source paragraph."""
    parts = []
    spans = []
    pos = 0
    for para in paragraphs:
        text = para["text"]
        start = pos
        parts.append(text)
        pos += len(text)
        spans.append((start, pos, para.get("page"), para["para_id"]))
        parts.append("\n")
        pos += 1
    return "".join(parts), spans


def locate_span(spans: list[tuple], offset: int) -> tuple:
    for start, end, page, para_id in spans:
        if start <= offset < end:
            return page, para_id
    return spans[-1][2], spans[-1][3]


def segment_lang(book: dict, lang: str) -> None:
    src = CLEANED_DIR / book["slug"] / f"{lang}.jsonl"
    if not src.exists():
        log.warning("  [skip] no cleaned %s source for %s", lang, book["slug"])
        return

    segmenter = SEGMENTERS[lang]
    paragraphs = read_jsonl(src)
    full_text, spans = join_paragraphs(paragraphs)

    sentences = []
    cursor = 0
    for sent_id, sent in enumerate(segmenter.segment(full_text)):
        idx = full_text.find(sent, cursor)
        if idx == -1:
            idx = full_text.find(sent)
        page, para_id = locate_span(spans, max(idx, 0))
        sentences.append(
            {
                "book": book["slug"],
                "lang": lang,
                "sent_id": sent_id,
                "source_page": page,
                "source_para_id": para_id,
                "text": sent,
            }
        )
        if idx != -1:
            cursor = idx + len(sent)

    write_jsonl(sentences, SEGMENTED_DIR / book["slug"] / f"{lang}.jsonl")
    log.info("  [ok] %s: %d sentences <- %d paragraphs", lang, len(sentences), len(paragraphs))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="comma-separated book slugs to segment (default: all)")
    args = parser.parse_args()
    wanted = set(args.only.split(",")) if args.only else None

    for book in BOOKS:
        if wanted and book["slug"] not in wanted:
            continue
        log.info("== %s (%s) ==", book["name"], book["slug"])
        segment_lang(book, "han")
        segment_lang(book, "viet")


if __name__ == "__main__":
    main()
