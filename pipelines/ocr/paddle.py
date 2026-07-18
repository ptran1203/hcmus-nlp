"""PaddleOCR-based text extraction, for PDF pages with no embedded text layer
(scanned-image books like chien_quoc_sach)."""
from .base import OCREngine


class PaddleOCREngine(OCREngine):
    def __init__(self, lang: str = "vi", device: str = "gpu:0"):
        self._lang = lang
        self._device = device
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            from paddleocr import PaddleOCR

            self._engine = PaddleOCR(lang=self._lang, use_angle_cls=True, device=self._device)
        return self._engine

    def extract_text(self, image_path: str) -> str:
        result = self.engine.ocr(image_path)
        lines = []
        for page_result in result:
            if not page_result:
                continue
            if isinstance(page_result, dict) and "rec_texts" in page_result:
                # PaddleOCR 3.x: unified pipeline result, dict-like with rec_texts
                lines.extend(page_result["rec_texts"])
            else:
                # PaddleOCR 2.x: nested [box, (text, confidence)] per line
                for _box, (text, _confidence) in page_result:
                    lines.append(text)
        return "\n".join(lines)
