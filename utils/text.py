"""Loose text matching for song titles and artist names."""

import re
import unicodedata


def normalize(text: str) -> str:
    """
    Compare-friendly form: no accents, case or punctuation.
    "Ivo Petrič & The Band" -> "ivopetricandband"
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"\bthe\b", " ", text)
    return re.sub(r"[^0-9a-z]+", "", text)


def same_name(a: str | None, b: str | None) -> bool:
    """Loose match: equal, or one contains the other ("Low Tides" ~ "The Low Tides")."""
    if not a or not b:
        return False
    a, b = normalize(a), normalize(b)
    return bool(a and b) and (a == b or a in b or b in a)
