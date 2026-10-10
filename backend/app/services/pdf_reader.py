from __future__ import annotations

from io import BytesIO
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader


MAX_PDF_BYTES = 12 * 1024 * 1024
MAX_TEXT_CHARS = 50000
MAX_PAGES = 40


def read_pdf_from_url(url: str) -> dict:
    if not url:
        return {
            "status": "error",
            "error": "PDF URL is required",
        }

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return {
            "status": "error",
            "error": "Only HTTP and HTTPS URLs are allowed",
        }

    try:
        headers = {
            "User-Agent": "EduCompass-Research/1.0"
        }

        with httpx.Client(
            follow_redirects=True,
            timeout=25,
            headers=headers,
        ) as client:

            response = client.get(url)
            response.raise_for_status()

            content = response.content

        if len(content) > MAX_PDF_BYTES:
            return {
                "status": "error",
                "error": "PDF exceeds maximum allowed size",
            }

        if not content.startswith(b"%PDF"):
            return {
                "status": "error",
                "error": "URL did not return a valid PDF",
            }

        reader = PdfReader(BytesIO(content))

        texts = []
        pages_read = min(len(reader.pages), MAX_PAGES)

        for page_number in range(pages_read):
            try:
                text = reader.pages[page_number].extract_text() or ""

                if text.strip():
                    texts.append(
                        f"\n--- PAGE {page_number + 1} ---\n{text}"
                    )

            except Exception:
                continue

        full_text = "".join(texts)

        if len(full_text) > MAX_TEXT_CHARS:
            full_text = full_text[:MAX_TEXT_CHARS]

        return {
            "status": "success",
            "url": url,
            "pages_total": len(reader.pages),
            "pages_read": pages_read,
            "text": full_text,
        }

    except Exception as exc:
        return {
            "status": "error",
            "url": url,
            "error": str(exc),
        }