from __future__ import annotations
import io
import re
from typing import Any, Dict, Tuple
from bs4 import BeautifulSoup
from pypdf import PdfReader


class ParseError(Exception):
    pass


def _clean_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_html(raw: bytes) -> Tuple[str, Dict[str, Any]]:
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = _clean_text(soup.get_text(separator="\n"))
    return text, {"title": title, "parser": "bs4_html"}


def parse_pdf(raw: bytes) -> Tuple[str, Dict[str, Any]]:
    reader = PdfReader(io.BytesIO(raw))
    pages = [f"\n\n[PAGE {i+1}]\n" + (page.extract_text() or "") for i, page in enumerate(reader.pages)]
    text = _clean_text("".join(pages))
    return text, {"pages": len(reader.pages), "parser": "pypdf"}


def extract_text(raw: bytes, mime_type: str) -> Tuple[str, Dict[str, Any]]:
    mt = (mime_type or "").lower()
    if "html" in mt or mt in {"text/plain", "application/xhtml+xml"}:
        return parse_html(raw)
    if "pdf" in mt or mt == "application/pdf":
        return parse_pdf(raw)
    try:
        txt = _clean_text(raw.decode("utf-8", errors="ignore"))
        if txt:
            return txt, {"parser": "utf8_fallback"}
    except Exception:
        pass
    raise ParseError(f"Unsupported/unparseable mime_type={mime_type}")
