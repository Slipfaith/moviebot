"""Utilities to extract movie titles from poster images."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Iterable, List, Optional

from .local_client import LocalOCRClient


@dataclass(slots=True)
class PosterRecognitionResult:
    """Structured result returned by :func:`recognize_poster_title`."""

    title: str
    raw_text: str
    candidates: List[str]

    def has_confident_title(self) -> bool:
        return bool(self.title.strip())


def _normalise_line(line: str) -> str:
    return re.sub(r"[^0-9A-Za-zА-Яа-яЁё'\- ]+", "", line).strip()


def _score_candidate(line: str) -> float:
    letters = sum(ch.isalpha() for ch in line)
    digits = sum(ch.isdigit() for ch in line)
    words = len(line.split())
    if letters == 0:
        return 0
    return letters + words * 0.5 - digits * 0.3


def _choose_best_candidate(lines: Iterable[str]) -> str:
    best_line = ""
    best_score = 0.0
    for raw in lines:
        normalised = _normalise_line(raw)
        if not normalised:
            continue
        score = _score_candidate(normalised)
        if score > best_score:
            best_score = score
            best_line = normalised
    return best_line


def recognize_poster_title(
    image_path: Path,
    *,
    client: Optional[LocalOCRClient] = None,
) -> PosterRecognitionResult:
    """Extract the most likely movie title from a poster image.

    Parameters
    ----------
    image_path:
        Path to the local image that should be processed.
    client:
        Optional :class:`LocalOCRClient` instance. If omitted a default client is
        created on demand. Having the parameter makes the function easy to mock
        during testing.
    """

    client = client or LocalOCRClient()
    raw_text = client.image_to_text(image_path)

    lines = client.image_to_lines(image_path)
    if not lines:
        lines = [line for line in raw_text.splitlines() if line.strip()]

    title = _choose_best_candidate(lines)
    return PosterRecognitionResult(title=title, raw_text=raw_text, candidates=lines)
