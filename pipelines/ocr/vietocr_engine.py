"""VietOCR-based text recognition, paired with EasyOCR's text detector.

VietOCR (pbcquoc/vietocr) is a Transformer-based recognizer trained
end-to-end on Vietnamese text -- it's specifically built to handle Vietnamese
diacritics/tone marks well, unlike generic multilingual OCR models. It only
recognizes a pre-cropped text line though; it doesn't locate text on a page.
So we pair it with EasyOCR purely for text *detection* (finding line boxes --
that part isn't Vietnamese-specific) and swap only the *recognition* step for
VietOCR. EasyOCR (not PaddleOCR) because it's PyTorch-based, and PyTorch is
already a dependency here (sentence-transformers) -- this avoids the
PaddlePaddle/PaddleOCR/paddlex dependency chain entirely, which turned out to
be too fragile (numpy ABI conflicts with several of paddlex's unrelated
transitive dependencies).
"""
from .base import OCREngine


class VietOCREngine(OCREngine):
    def __init__(self, detector_langs: list[str] | None = None, device: str = "cuda:0"):
        self._detector_langs = detector_langs or ["vi"]
        self._device = device
        self._detector = None
        self._recognizer = None

    @property
    def detector(self):
        if self._detector is None:
            import easyocr

            gpu = self._device.startswith(("cuda", "gpu"))
            self._detector = easyocr.Reader(self._detector_langs, gpu=gpu)
        return self._detector

    @property
    def recognizer(self):
        if self._recognizer is None:
            from vietocr.tool.config import Cfg
            from vietocr.tool.predictor import Predictor

            config = Cfg.load_config_from_name("vgg_transformer")
            config["device"] = self._device
            config["predictor"]["beamsearch"] = False
            self._recognizer = Predictor(config)
        return self._recognizer

    def extract_text(self, image_path: str) -> str:
        from PIL import Image

        horizontal_list, free_list = self.detector.detect(image_path)
        full_image = Image.open(image_path).convert("RGB")

        boxes = []  # (x0, y0, x1, y1)
        for x_min, x_max, y_min, y_max in horizontal_list[0]:
            boxes.append((x_min, y_min, x_max, y_max))
        for quad in free_list[0]:
            xs = [pt[0] for pt in quad]
            ys = [pt[1] for pt in quad]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))

        lines = []
        for x0, y0, x1, y1 in boxes:
            crop = full_image.crop((x0, y0, x1, y1))
            text = self.recognizer.predict(crop)
            lines.append((y0, text))

        lines.sort(key=lambda item: item[0])  # reading order, top to bottom
        return "\n".join(text for _, text in lines)
