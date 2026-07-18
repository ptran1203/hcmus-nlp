"""Shared PDF text extraction (with OCR fallback), used by both 01_clean.py
and 04_export.py so raw-text export and cleaning always see the same text --
including OCR output for scanned-image PDFs (e.g. chien_quoc_sach's viet.pdf).

Extraction result is cached to <slug>/viet_raw.txt next to the source PDF:
this *is* the "OCR thô" raw-text artifact the assignment asks for, and
caching it means OCR (the slow step) only ever runs once per book, no matter
how many times 01_clean.py / 04_export.py are re-run.
"""
import tempfile
from pathlib import Path

from tqdm import tqdm

from ocr.vietocr_engine import VietOCREngine

OCR_ENGINE = VietOCREngine()
PAGE_DELIMITER = "\n\n<<<PAGE_BREAK>>>\n\n"
MARGIN_PCT = 0.08  # trim this fraction off each edge before OCR -- cuts running
# headers/footers/page-numbers/binding-shadow noise, and shrinks the OCR'd area


def ocr_page(page) -> str:
    import fitz  # PyMuPDF

    rect = page.rect
    dx, dy = rect.width * MARGIN_PCT, rect.height * MARGIN_PCT
    clip = fitz.Rect(rect.x0 + dx, rect.y0 + dy, rect.x1 - dx, rect.y1 - dy)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        page.get_pixmap(dpi=200, clip=clip).save(tmp_path)
        return OCR_ENGINE.extract_text(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    import fitz  # PyMuPDF

    raw_txt_path = path.with_name(f"{path.stem}_raw.txt")
    if raw_txt_path.exists():
        texts = raw_txt_path.read_text(encoding="utf-8").split(PAGE_DELIMITER)
        return list(enumerate(texts, start=1))

    pages = []
    with fitz.open(path) as doc:
        for i, page in enumerate(tqdm(doc, desc=f"Extracting {path.name}"), start=1):
            text = page.get_text("text")
            if not text.strip():
                text = ocr_page(page)
            pages.append((i, text))

    raw_txt_path.write_text(PAGE_DELIMITER.join(text for _, text in pages), encoding="utf-8")
    return pages
