"""ICU line-boundary authority and dictionary hyphenation candidates."""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class UnicodeAuthorityUnavailable(RuntimeError):
    pass


class BreakKind(StrEnum):
    SOFT = "soft"
    HARD = "hard"
    HYPHEN = "hyphen"


@dataclass(frozen=True, slots=True)
class BreakOpportunity:
    index: int
    kind: BreakKind
    penalty: int = 0


def line_break_opportunities(text: str, *, language: str = "und") -> tuple[BreakOpportunity, ...]:
    """Return ICU line boundaries as Python code-point offsets."""

    try:
        icu = importlib.import_module("icu")
    except ImportError as error:
        raise UnicodeAuthorityUnavailable(
            "ICU line breaking requires the 'unicode' extra and system ICU development files"
        ) from error
    iterator = icu.BreakIterator.createLineInstance(icu.Locale(language))
    iterator.setText(text)
    utf16_map = _utf16_to_codepoint_map(text)
    opportunities: list[BreakOpportunity] = []
    iterator.first()
    while True:
        raw_boundary = int(iterator.nextBoundary())
        if raw_boundary == int(icu.BreakIterator.DONE):
            break
        index = _codepoint_index(raw_boundary, text, utf16_map)
        status = int(iterator.getRuleStatus())
        kind = BreakKind.HARD if 100 <= status < 200 else BreakKind.SOFT
        opportunities.append(BreakOpportunity(index, kind))
    if not opportunities or opportunities[-1].index != len(text):
        opportunities.append(BreakOpportunity(len(text), BreakKind.HARD))
    return _deduplicate(opportunities)


def hyphenation_opportunities(
    text: str,
    *,
    language: str,
    minimum_word_length: int = 5,
    minimum_prefix: int = 2,
    minimum_suffix: int = 2,
    penalty: int = 50,
) -> tuple[BreakOpportunity, ...]:
    """Return Pyphen dictionary candidates without mutating authored text."""

    try:
        pyphen = importlib.import_module("pyphen")
    except ImportError as error:
        raise UnicodeAuthorityUnavailable(
            "dictionary hyphenation requires the 'typography' extra"
        ) from error
    dictionary: Any = pyphen.Pyphen(lang=language, left=minimum_prefix, right=minimum_suffix)
    opportunities: list[BreakOpportunity] = []
    for match in re.finditer(r"[^\W\d_]+", text, re.UNICODE):
        word = match.group(0)
        if len(word) < minimum_word_length:
            continue
        for position in dictionary.positions(word):
            opportunities.append(
                BreakOpportunity(match.start() + int(position), BreakKind.HYPHEN, penalty)
            )
    return tuple(opportunities)


def _utf16_to_codepoint_map(text: str) -> dict[int, int]:
    units = 0
    result = {0: 0}
    for index, character in enumerate(text, start=1):
        units += len(character.encode("utf-16-le")) // 2
        result[units] = index
    return result


def _codepoint_index(raw: int, text: str, utf16_map: dict[int, int]) -> int:
    mapped = utf16_map.get(raw)
    if mapped is not None:
        return mapped
    if 0 <= raw <= len(text):
        return raw
    raise UnicodeAuthorityUnavailable(f"ICU returned an invalid line boundary offset: {raw}")


def _deduplicate(opportunities: list[BreakOpportunity]) -> tuple[BreakOpportunity, ...]:
    priority = {BreakKind.SOFT: 0, BreakKind.HYPHEN: 1, BreakKind.HARD: 2}
    result: dict[int, BreakOpportunity] = {}
    for opportunity in opportunities:
        previous = result.get(opportunity.index)
        if previous is None or priority[opportunity.kind] > priority[previous.kind]:
            result[opportunity.index] = opportunity
    return tuple(result[index] for index in sorted(result))
