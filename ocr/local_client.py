"""Local OCR client powered by Tesseract via :mod:`pytesseract`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from PIL import Image
import pytesseract


@dataclass(slots=True)
class LocalOCRClient:
    """A tiny wrapper around :func:`pytesseract.image_to_data`.

    Parameters
    ----------
    languages:
        Languages passed to Tesseract. By default both English and Russian are
        enabled as requested by the bot requirements.
    psm:
        Page segmentation mode. ``3`` (fully automatic) works well for posters.
    oem:
        OCR Engine mode. ``3`` allows Tesseract to pick the best engine
        available locally.
    """

    languages: str = "eng+rus"
    psm: int = 3
    oem: int = 3

    def image_to_text(self, image_path: Path) -> str:
        """Return raw text extracted from *image_path*.

        The method performs a light pre-processing step (conversion to grayscale)
        before delegating the heavy lifting to Tesseract. The conversion improves
        the quality of recognition on colourful posters without requiring OpenCV
        or other heavy dependencies.
        """

        with Image.open(image_path) as image:
            grayscale = image.convert("L")
            config = f"--psm {self.psm} --oem {self.oem}"
            return pytesseract.image_to_string(grayscale, lang=self.languages, config=config)

    def image_to_lines(self, image_path: Path) -> List[str]:
        """Return recognised lines with confidence scores.

        Tesseract returns a TSV table with one row per element. We aggregate
        recognised words into lines ordered by their confidence.
        """

        with Image.open(image_path) as image:
            grayscale = image.convert("L")
            config = f"--psm {self.psm} --oem {self.oem}"
            data = pytesseract.image_to_data(
                grayscale, lang=self.languages, config=config, output_type=pytesseract.Output.DICT
            )

        lines: dict[int, list[str]] = {}
        for text, conf, line_no in zip(data["text"], data["conf"], data["line"], strict=False):
            if not text.strip():
                continue
            if int(conf) < 0:
                # Tesseract uses -1 to indicate "not sure".
                continue
            lines.setdefault(line_no, []).append(text.strip())

        ordered = [" ".join(words) for _, words in sorted(lines.items()) if words]
        return ordered
