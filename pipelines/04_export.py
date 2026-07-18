"""Export final deliverables per book, per the assignment's required format:

  - <slug>_raw.txt       : raw OCR/extracted text (before cleaning) for the
                           Vietnamese side, when the source was a PDF/image.
  - <slug>_parallel.tsv  : final aligned pairs, columns
                           pair_id \t han_sentence \t viet_sentence
  - <slug>_parallel.xlsx : same data as an Excel file

Reads dataset/raw/<slug>/viet.pdf and dataset/aligned/<slug>.tsv, writing to
dataset/deliverables/. Uses each book's slug in place of the "[matacpham]"
(work code) placeholder in the filenames.

Usage:
    python pipelines/04_export.py [--only slug1,slug2]
"""
import argparse
import csv
import logging
from pathlib import Path

import pandas as pd

from config import BOOKS, CLEANED_DIR, RAW_DIR
from pdf_extract import extract_pdf_pages

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

ALIGNED_DIR = CLEANED_DIR.parent / "aligned"
DELIVERABLES_DIR = CLEANED_DIR.parent / "deliverables"


def export_raw_text(book: dict) -> None:
    viet_path = RAW_DIR / book["slug"] / "viet.pdf"
    if not viet_path.exists():
        log.warning("  [skip] no viet.pdf for %s, skipping raw.txt", book["slug"])
        return

    pages = extract_pdf_pages(viet_path)  # falls back to OCR per-page when needed
    raw_text = "\n\n".join(text for _page_no, text in pages)

    if not raw_text.strip():
        log.warning("  [warn] %s: no extractable text even after OCR, raw.txt not written", book["slug"])
        return

    out_path = DELIVERABLES_DIR / f"{book['slug']}_raw.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(raw_text, encoding="utf-8")
    log.info("  [ok] raw.txt: %d pages -> %s", len(pages), out_path.name)


def export_parallel(book: dict) -> None:
    src = ALIGNED_DIR / f"{book['slug']}.tsv"
    if not src.exists():
        log.warning("  [skip] no aligned TSV for %s", book["slug"])
        return

    with src.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    records = [
        {"pair_id": i, "han_sentence": r["han"], "viet_sentence": r["viet"]}
        for i, r in enumerate(rows, start=1)
    ]

    DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)

    tsv_path = DELIVERABLES_DIR / f"{book['slug']}_parallel.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["pair_id", "han_sentence", "viet_sentence"])
        for rec in records:
            writer.writerow([rec["pair_id"], rec["han_sentence"], rec["viet_sentence"]])

    xlsx_path = DELIVERABLES_DIR / f"{book['slug']}_parallel.xlsx"
    pd.DataFrame(records).to_excel(xlsx_path, index=False)

    log.info("  [ok] parallel: %d pairs -> %s, %s", len(records), tsv_path.name, xlsx_path.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="comma-separated book slugs to export (default: all)")
    args = parser.parse_args()
    wanted = set(args.only.split(",")) if args.only else None

    for book in BOOKS:
        if wanted and book["slug"] not in wanted:
            continue
        log.info("== %s (%s) ==", book["name"], book["slug"])
        export_raw_text(book)
        export_parallel(book)


if __name__ == "__main__":
    main()
