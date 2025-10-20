"""OCR pipeline used to extract movie titles from poster images."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from .local_client import LocalOCRClient


@dataclass
class PosterOCR:
    """Poster-specific OCR helper based on EasyOCR."""

    languages: Sequence[str] = ("ru", "en")
    gpu: bool = False
    min_confidence: float = 0.35
    local_client: Optional[LocalOCRClient] = None

    def __post_init__(self) -> None:
        self._reader = None
        if self.local_client is None:
            self.local_client = LocalOCRClient.from_env()

    def _ensure_reader(self):
        if self.local_client:
            return None
        if self._reader is None:
            import easyocr  # imported lazily to speed up cold starts

            self._reader = easyocr.Reader(list(self.languages), gpu=self.gpu)
        return self._reader

    @staticmethod
    def _prepare_image(image_bytes: bytes) -> np.ndarray:
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        return np.array(image)

    def _post_process(self, candidates: Iterable[Tuple[str, float]]) -> List[str]:
        normalized: List[Tuple[str, float]] = []
        seen = set()
        for text, score in candidates:
            cleaned = re.sub(r"\s+", " ", text.strip())
            cleaned = cleaned.strip("-•·—")
            if not cleaned:
                continue
            lower = cleaned.lower()
            if lower in seen:
                continue
            seen.add(lower)
            bonus = 0.0
            if cleaned.isupper():
                bonus += 0.1
            if any(ch.isalpha() for ch in cleaned):
                bonus += 0.1
            normalized.append((cleaned, score + bonus))
        normalized.sort(key=lambda item: item[1], reverse=True)
        return [text for text, _ in normalized]

    def extract_candidates(self, image_bytes: bytes) -> List[str]:
        """Return OCR candidates sorted by confidence."""

        if self.local_client:
            return self._post_process(
                ((line, 1.0) for line in self.local_client.recognize(image_bytes))
            )

        reader = self._ensure_reader()
        if reader is None:
            return []

        image = self._prepare_image(image_bytes)
        results = reader.readtext(image, detail=1)
        extracted: List[Tuple[str, float]] = []
        for *_, text, confidence in results:
            if confidence < self.min_confidence:
                continue
            extracted.append((text, confidence))
        return self._post_process(extracted)

    def extract_title(self, image_bytes: bytes) -> Optional[str]:
        """Shortcut that returns the most promising candidate."""

        candidates = self.extract_candidates(image_bytes)
        return candidates[0] if candidates else None


_default_ocr: Optional[PosterOCR] = None


def get_default_ocr() -> PosterOCR:
    global _default_ocr
    if _default_ocr is None:
        _default_ocr = PosterOCR()
    return _default_ocr

