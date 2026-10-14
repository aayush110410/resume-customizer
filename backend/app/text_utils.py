"""Text normalization shared by grounding, keyword matching and scoring."""

import math
import re
import unicodedata
from functools import lru_cache

_TRANSLATE = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        "−": "-",
        " ": " ",
        "­": None,  # soft hyphen
        "•": " ",  # •
        "▪": " ",  # ▪
        "●": " ",  # ●
        "◦": " ",  # ◦
        "·": " ",  # ·
        "​": None,  # zero-width space
    }
)
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Canonical form for comparing PDF-extracted text with LLM output: ligatures, quotes, dashes, glyphs."""
    text = unicodedata.normalize("NFKC", text).translate(_TRANSLATE)
    return _WS.sub(" ", text).strip().lower()


@lru_cache(maxsize=8192)
def _term_pattern(term: str) -> re.Pattern[str]:
    # A term is "word-bounded" only on sides where it begins/ends with a word character, so `c++` and `.net`
    # still match while `go` does not match inside `golang`.
    core = re.escape(term)
    left = r"(?<![\w])" if term[:1].isalnum() or term[:1] == "_" else r"(?<![\w.])"
    right = r"(?![\w+#])" if term[-1:].isalnum() or term[-1:] == "_" else r"(?![\w])"
    return re.compile(left + core + right)


def contains_term(haystack: str, term: str) -> bool:
    term = normalize(term)
    if not term:
        return False
    return _term_pattern(term).search(normalize(haystack)) is not None


def estimate_pages(word_count: int) -> int:
    return max(1, math.ceil(word_count / 550))
