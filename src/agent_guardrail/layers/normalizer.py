from __future__ import annotations

import html
import re
import unicodedata
from urllib.parse import unquote


ZERO_WIDTH = re.compile(r"[\u200B\u200C\u200D\uFEFF]")
SPACES = re.compile(r"\s+")


class TextNormalizer:
    def normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        normalized = unquote(normalized)
        normalized = html.unescape(normalized)
        normalized = ZERO_WIDTH.sub("", normalized)
        normalized = normalized.lower()
        normalized = SPACES.sub(" ", normalized).strip()
        return normalized
