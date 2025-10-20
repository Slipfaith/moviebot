"""Helper for delegating OCR to a locally running service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests

from core.config import OCR_LOCAL_URL


@dataclass
class LocalOCRClient:
    """Simple HTTP client that talks to a locally running OCR service.

    The client expects the service to expose a POST ``/ocr`` endpoint that
    accepts multipart form uploads under the ``file`` field and returns JSON of
    the form ``{"text": ["line1", "line2", ...]}``.
    """

    base_url: str
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> Optional["LocalOCRClient"]:
        """Create a client when ``OCR_LOCAL_URL`` is defined."""

        base_url = OCR_LOCAL_URL
        if not base_url:
            return None
        return cls(base_url=base_url.rstrip("/"))

    def recognize(self, image_bytes: bytes) -> List[str]:
        """Send the image to the local OCR endpoint and return text lines."""

        response = requests.post(
            f"{self.base_url}/ocr",
            files={"file": ("poster.jpg", image_bytes, "image/jpeg")},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        data: Iterable[str] = payload.get("text", [])
        return [item.strip() for item in data if isinstance(item, str) and item.strip()]

