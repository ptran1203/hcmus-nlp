"""Clean raw sources into paragraph-level JSONL files.

Han sources are plain text (possibly non-UTF-8 encoded). Viet sources are
PDFs and need text extraction first. Output goes to dataset/cleaned/<slug>/
{han,viet}.jsonl, one paragraph per line, keeping page/paragraph provenance
so later segmentation & alignment steps can trace text back to its source.

Usage:
    python pipelines/01_clean.py [--only slug1,slug2]
"""
import argparse
import json
import logging
from pathlib import Path

from config import BOOKS, CLEANED_DIR, RAW_DIR
from text_clean import clean_text, split_paragraphs

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

TEXT_ENCODINGS = ["utf-8-sig", "utf-8", "gb18030", "big5"]


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in TEXT_ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    import fitz  # PyMuPDF

    pages = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            pages.append((i, page.get_text("text")))
    return pages


def write_jsonl(records: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def dedup_exact(items: list, key=lambda x: x) -> tuple[list, int]:
    """Drop items whose key exactly matches an earlier item's key, keeping the
    first occurrence. Source files can contain accidental duplicate blocks
    (e.g. a botched OCR/extraction re-run); this removes them before they
    inflate downstream sentence counts."""
    seen = set()
    out = []
    dropped = 0
    for item in items:
        k = key(item)
        if k in seen:
            dropped += 1
            continue
        seen.add(k)
        out.append(item)
    return out, dropped


def clean_han(book: dict, raw_folder: Path) -> None:
    matches = list(raw_folder.glob("han.*"))
    if not matches:
        log.warning("  [skip] no han source for %s", book["slug"])
        return
    src = matches[0]
    text = clean_text(read_text_file(src))
    paragraphs, n_dropped = dedup_exact(split_paragraphs(text))
    if n_dropped:
        log.warning("  [dedup] dropped %d duplicate han paragraphs", n_dropped)
    records = [
        {"book": book["slug"], "lang": "han", "page": None, "para_id": i, "text": p}
        for i, p in enumerate(paragraphs)
    ]
    write_jsonl(records, CLEANED_DIR / book["slug"] / "han.jsonl")
    log.info("  [ok] han: %d paragraphs <- %s", len(records), src.name)


def clean_viet(book: dict, raw_folder: Path) -> None:
    matches = list(raw_folder.glob("viet.*"))
    if not matches:
        log.warning("  [skip] no viet source for %s", book["slug"])
        return
    src = matches[0]

    if src.suffix.lower() == ".pdf":
        page_paragraphs = [
            (page_no, p)
            for page_no, raw_page in extract_pdf_pages(src)
            for p in split_paragraphs(clean_text(raw_page))
        ]
        page_paragraphs, n_dropped = dedup_exact(page_paragraphs, key=lambda x: x[1])
        if n_dropped:
            log.warning("  [dedup] dropped %d duplicate viet paragraphs", n_dropped)
        records = [
            {"book": book["slug"], "lang": "viet", "page": page_no, "para_id": i, "text": p}
            for i, (page_no, p) in enumerate(page_paragraphs)
        ]
    else:
        text = clean_text(read_text_file(src))
        paragraphs, n_dropped = dedup_exact(split_paragraphs(text))
        if n_dropped:
            log.warning("  [dedup] dropped %d duplicate viet paragraphs", n_dropped)
        records = [
            {"book": book["slug"], "lang": "viet", "page": None, "para_id": i, "text": p}
            for i, p in enumerate(paragraphs)
        ]

    write_jsonl(records, CLEANED_DIR / book["slug"] / "viet.jsonl")
    log.info("  [ok] viet: %d paragraphs <- %s", len(records), src.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="comma-separated book slugs to clean (default: all)")
    args = parser.parse_args()
    wanted = set(args.only.split(",")) if args.only else None

    for book in BOOKS:
        if wanted and book["slug"] not in wanted:
            continue
        log.info("== %s (%s) ==", book["name"], book["slug"])
        raw_folder = RAW_DIR / book["slug"]
        clean_han(book, raw_folder)
        clean_viet(book, raw_folder)


if __name__ == "__main__":
    main()
