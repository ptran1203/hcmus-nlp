"""Quick one-off: rebuild a book's raw.txt deliverable from its already-cleaned
viet.jsonl, for when the pre-cleaning OCR cache (dataset/raw/<slug>/viet_raw.txt)
wasn't produced (e.g. cleaned before OCR caching was added). Note this is the
*cleaned* text, not the literal pre-cleaning OCR output.

Usage:
    python pipelines/jsonl_to_raw.py <slug>
"""
import json
import sys
from pathlib import Path

from config import CLEANED_DIR

DELIVERABLES_DIR = CLEANED_DIR.parent / "deliverables"


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python pipelines/jsonl_to_raw.py <slug>")
        sys.exit(1)
    slug = sys.argv[1]

    src = CLEANED_DIR / slug / "viet.jsonl"
    records = [json.loads(line) for line in src.open(encoding="utf-8") if line.strip()]
    raw_text = "\n\n".join(r["text"] for r in records)

    out_path = DELIVERABLES_DIR / f"{slug}_raw.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(raw_text, encoding="utf-8")
    print(f"[ok] {len(records)} paragraphs -> {out_path}")


if __name__ == "__main__":
    main()
