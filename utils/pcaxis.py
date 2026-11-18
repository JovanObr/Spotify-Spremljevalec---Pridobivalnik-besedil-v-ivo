"""
A small parser for PC-Axis (.px) files, the format statistical offices use
for multi-dimensional tables (SiStat, Statistics Sweden, ...).

A .px file is a list of KEYWORD=value; statements followed by the numbers:

    CHARSET="ANSI";
    TITLE[en]="Concerts by type of music, Slovenia";
    STUB="TYPE OF MUSIC";
    HEADING="YEAR";
    VALUES("TYPE OF MUSIC")="Choral","Pop and rock";
    VALUES("YEAR")="2022","2023";
    UNITS="number";
    DATA=
    1200 1250
    310 ".." ;

DATA lists every cell in order: the STUB dimensions vary slowest, the
HEADING dimensions fastest (the last heading changes on every number).
Missing values are written as dots or dashes ("..", "-", ".").
"""

import itertools
import re
from dataclasses import dataclass, field


MISSING_MARKERS = {".", "..", "...", "....", "-", ":", "x", '"."', '".."', '"..."', '"-"', '":"'}


class PxError(ValueError):
    """The file isn't valid PC-Axis."""


@dataclass
class PxTable:
    title: str
    dimensions: list[tuple[str, list[str]]]  # (name, value labels), in DATA order
    data: dict[tuple[str, ...], float | None]
    units: str | None = None
    contents: str | None = None
    source: str | None = None
    last_updated: str | None = None
    notes: list[str] = field(default_factory=list)
    codes: dict[str, list[str]] = field(default_factory=dict)

    def value(self, **coords: str) -> float | None:
        key = tuple(coords[name] for name, _ in self.dimensions)
        return self.data.get(key)


# One statement: KEYWORD, optional [lang], optional ("subkey"), =, value up to ;
_STATEMENT = re.compile(
    r'\s*(?P<key>[A-Z0-9-]+)(?:\[(?P<lang>[^\]]+)\])?(?:\((?P<sub>(?:"[^"]*"|[^)])*)\))?\s*=',
    re.S,
)


def _decode(raw: bytes) -> str:
    head = raw[:4000].decode("ascii", "ignore")
    match = re.search(r'CODEPAGE\s*=\s*"([^"]+)"', head)
    encodings = [match.group(1)] if match else []
    encodings += ["utf-8", "windows-1250", "latin-1"]
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("latin-1")


def _strings(value: str) -> list[str]:
    """The quoted strings in a value ("a","b" or "a" "b" across lines)."""
    return [part.replace('""', '"') for part in re.findall(r'"((?:[^"]|"")*)"', value)]


def _split_statements(text: str):
    """(key, lang, subkey, raw value) for every statement before DATA, and the DATA text."""
    position = 0
    statements = []
    while True:
        match = _STATEMENT.match(text, position)
        if not match:
            break
        key = match.group("key")
        start = match.end()
        if key == "DATA":
            end = text.find(";", start)
            return statements, text[start: end if end != -1 else len(text)]
        # The value ends at the first ; outside quotes
        index, in_quotes = start, False
        while index < len(text):
            char = text[index]
            if char == '"':
                in_quotes = not in_quotes
            elif char == ";" and not in_quotes:
                break
            index += 1
        sub = match.group("sub")
        statements.append((key, match.group("lang"), _strings(sub)[0] if sub and '"' in sub else sub, text[start:index].strip()))
        position = index + 1
    raise PxError("No DATA section found.")


def parse(raw: bytes | str, language: str | None = None) -> PxTable:
    """
    Parse a .px file. With several languages in one file, `language`
    picks one (default: the file's main language).
    """
    text = raw if isinstance(raw, str) else _decode(raw)
    statements, data_text = _split_statements(text)

    main_language = None
    for key, lang, sub, value in statements:
        if key == "LANGUAGE" and lang is None:
            main_language = (_strings(value) or [None])[0]
    wanted = None if language in (None, main_language) else language

    def pick(key, sub=None):
        """The statement for this key (and subkey) in the wanted language."""
        fallback = None
        for k, lang, s, value in statements:
            if k != key or (sub is not None and s != sub):
                continue
            if lang == wanted:
                return value
            if lang is None and fallback is None:
                fallback = value
        return fallback

    def pick_all(key):
        return [(s, value) for k, lang, s, value in statements if k == key and lang == wanted] or [
            (s, value) for k, lang, s, value in statements if k == key and lang is None
        ]

    stub = _strings(pick("STUB") or "")
    heading = _strings(pick("HEADING") or "")
    names = stub + heading
    if not names:
        raise PxError("The table has no STUB or HEADING dimensions.")

    values = dict((s, _strings(v)) for s, v in pick_all("VALUES"))
    codes = dict((s, _strings(v)) for s, v in pick_all("CODES"))
    dimensions = []
    for name in names:
        if name not in values:
            raise PxError(f'VALUES("{name}") is missing.')
        dimensions.append((name, values[name]))

    tokens = re.findall(r'"[^"]*"|[^\s,;]+', data_text)
    cells: list[float | None] = []
    for token in tokens:
        if token in MISSING_MARKERS or token.strip('"') in MISSING_MARKERS:
            cells.append(None)
            continue
        try:
            cells.append(float(token.strip('"')))
        except ValueError:
            cells.append(None)

    expected = 1
    for _, labels in dimensions:
        expected *= len(labels)
    if len(cells) != expected:
        raise PxError(f"DATA has {len(cells)} numbers, the dimensions need {expected}.")

    combos = itertools.product(*(labels for _, labels in dimensions))
    data = dict(zip(combos, cells))

    notes = [n for _, value in pick_all("NOTE") for n in _strings(value)]
    notes += [n for _, value in pick_all("NOTEX") for n in _strings(value)]

    def first(key):
        value = pick(key)
        return (_strings(value) or [None])[0] if value else None

    return PxTable(
        title=first("TITLE") or first("CONTENTS") or "",
        dimensions=dimensions,
        data=data,
        units=first("UNITS"),
        contents=first("CONTENTS"),
        source=first("SOURCE"),
        last_updated=first("LAST-UPDATED"),
        notes=notes,
        codes=codes,
    )
