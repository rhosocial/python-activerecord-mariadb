# src/rhosocial/activerecord/backend/impl/mariadb/_scan.py
"""Regex-free character scanning for MariaDB's read-direction parsers.

The backend reads a handful of server spellings back into values -- a
column's declared type, a type's charset/collation, a spatial reference
system, a server version. Those reads are small, fixed grammars, and this
module expresses them as plain character scans so that ``src`` never needs the
standard library's regular-expression module.

Every helper states what it accepts, because "the same thing the regex did" is
not a specification a reader can check: the functions below are equivalent to
the patterns named in their docstrings, including the edge cases that matter
for a round trip (an empty word run, a digit-free group, an unterminated
quote). Inputs these parsers see come from the server's catalog, so the scans
are total: no exceptions, ``None`` for "not present".
"""

from typing import List, Optional, Sequence


def _is_word_char(ch: str) -> bool:
    """Whether ``ch`` belongs to ``\\w``: a letter or digit, or the underscore."""
    return ch.isalnum() or ch == "_"


def _is_decimal_digit(ch: str) -> bool:
    """Whether ``ch`` belongs to ``\\d`` (a Unicode decimal digit)."""
    return ch.isdecimal()


def leading_word(text: str) -> str:
    """Return the run of ``\\w`` characters at the start of ``text``.

    The result is the word a ``^WORD\\b`` prefix match would have tested: the
    scan stops at the first non-word character, which is exactly where ``\\b``
    sits. An empty string is returned when the text starts with a non-word
    character.
    """
    end = 0
    while end < len(text) and _is_word_char(text[end]):
        end += 1
    return text[:end]


def leading_word_matches(text: str, words: Sequence[str]) -> bool:
    """Whether ``text`` starts with one of ``words``, compared case-insensitively.

    Equivalent to matching the pattern ``^(?:a|b|...)\\b`` at the start with the
    ignore-case flag, for a closed, non-empty set of words: the leading word is
    read whole and compared against the set, so a word that merely *starts
    with* a candidate (``INT8`` against ``INT``) is not a match. The set must
    contain upper-case words.
    """
    word = leading_word(text)
    return bool(word) and word.upper() in words


def leading_ascii_uppercase(text: str) -> str:
    """Return the run of ASCII ``A``-``Z`` letters at the start of ``text``.

    Equivalent to matching the pattern ``[A-Z]+`` at the start: only ASCII
    upper-case letters count, so a digit ends the run. An empty string means
    the text does not start with an upper-case word.
    """
    end = 0
    while end < len(text) and "A" <= text[end] <= "Z":
        end += 1
    return text[:end]


def word_run(text: str, start: int = 0) -> str:
    """Return the run of ``\\w`` characters beginning at ``start``.

    Equivalent to the group of ``\\w+`` matched at that offset; an empty string
    means no word starts there.
    """
    end = start
    while end < len(text) and _is_word_char(text[end]):
        end += 1
    return text[start:end]


def _skip_whitespace(text: str, start: int, required: bool) -> Optional[int]:
    """Return the offset after a run of whitespace, or ``None`` when disallowed.

    With ``required=True`` at least one whitespace character must be present,
    which is ``\\s+``; with ``required=False`` zero characters are fine, which
    is ``\\s*``.
    """
    end = start
    while end < len(text) and text[end].isspace():
        end += 1
    if required and end == start:
        return None
    return end


def word_after(text: str, keywords: Sequence[str]) -> Optional[str]:
    """Return the ``\\w+`` word that follows a phrase, or ``None``.

    ``keywords`` is the literal phrase, one or more words separated by at least
    one whitespace character. The leftmost occurrence wins, as a leftmost
    pattern search would; if an occurrence is not followed by a word the scan
    goes on to the next one, as the regex engine would.

    Examples of the patterns this replaces:
    ``CHARACTER\\s+SET\\s+(\\w+)`` is ``word_after(text, ("CHARACTER", "SET"))``
    and ``COLLATE\\s+(\\w+)`` is ``word_after(text, ("COLLATE",))``. ``text`` is
    expected to be already upper-cased by the caller, so keyword matching is
    exact.
    """
    start = 0
    while True:
        at = text.find(keywords[0], start)
        if at < 0:
            return None
        position = at + len(keywords[0])
        for keyword in keywords[1:]:
            skipped = _skip_whitespace(text, position, required=True)
            if skipped is None or not text.startswith(keyword, skipped):
                break
            position = skipped + len(keyword)
        else:
            skipped = _skip_whitespace(text, position, required=True)
            if skipped is not None:
                word = word_run(text, skipped)
                if word:
                    return word
        start = at + 1


def digits_after_marker(text: str, marker: str) -> Optional[int]:
    """Return the number written after ``marker=<digits>``, or ``None``.

    Equivalent to searching the text for the pattern ``<marker>\\s*=\\s*(\\d+)``:
    whitespace before and after ``=`` is optional, but the marker itself and
    the ``=`` are literal, and at least one decimal digit must follow.
    """
    start = 0
    while True:
        at = text.find(marker, start)
        if at < 0:
            return None
        position = _skip_whitespace(text, at + len(marker), required=False)
        if text.startswith("=", position):
            digits_at = _skip_whitespace(text, position + 1, required=False)
            digits = _decimal_run_at(text, digits_at)
            if digits:
                return int(digits)
        start = at + 1


def _matching_close(text: str, open_at: int) -> int:
    """Return the offset of the ``)`` balancing the ``(`` at ``open_at``, or ``-1``.

    Parentheses inside single-quoted literals are ignored, so a quoted ``'('``
    cannot unbalance a group. ``-1`` means the group is never closed.
    """
    depth = 0
    quoted = False
    for index in range(open_at, len(text)):
        ch = text[index]
        if quoted:
            if ch == "'":
                quoted = False
            continue
        if ch == "'":
            quoted = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def parenthesized(text: str, start: int = 0) -> Optional[str]:
    """Return the contents of the first balanced ``(...)`` at or after ``start``.

    The scan starts at each ``(`` in turn and takes the one whose group closes,
    which is what a leftmost regex search does: an unmatched ``(`` earlier in
    the text does not hide a later, balanced group. ``None`` means no group
    closes.
    """
    open_at = text.find("(", start)
    while open_at >= 0:
        close_at = _matching_close(text, open_at)
        if close_at >= 0:
            return text[open_at + 1 : close_at]
        open_at = text.find("(", open_at + 1)
    return None


def _decimal_run_at(text: str, start: int) -> str:
    """Return the run of decimal digits beginning at ``start``."""
    end = start
    while end < len(text) and _is_decimal_digit(text[end]):
        end += 1
    return text[start:end]


def digit_runs(text: str) -> List[int]:
    """Return every run of decimal digits in ``text``, in order, as integers.

    Equivalent to turning every ``\\d+`` match in ``text`` into an integer: the
    runs are maximal, non-adjacent, and ignore every other character.
    """
    runs: List[int] = []
    digits: List[str] = []
    for ch in text:
        if _is_decimal_digit(ch):
            digits.append(ch)
            continue
        if digits:
            runs.append(int("".join(digits)))
            digits = []
    if digits:
        runs.append(int("".join(digits)))
    return runs


def parenthesized_number(text: str, allow_whitespace: bool = False) -> Optional[int]:
    """Return the number of the first ``(<digits>)`` group, or ``None``.

    Equivalent to searching for the pattern ``\\(\\s*(\\d+)\\s*\\)`` when
    ``allow_whitespace`` is true, and for ``\\((\\d+)\\)`` when it is false.
    A group whose contents are not exactly one digit run is
    skipped and the next group is tried, which is the leftmost-match rule; an
    empty or absent group yields ``None``.
    """
    open_at = text.find("(")
    while open_at >= 0:
        close_at = _matching_close(text, open_at)
        if close_at >= 0:
            inner = text[open_at + 1 : close_at]
            probe = inner.strip() if allow_whitespace else inner
            if probe and all(_is_decimal_digit(ch) for ch in probe):
                return int(probe)
        open_at = text.find("(", open_at + 1)
    return None


def single_quoted(text: str) -> List[str]:
    """Return the contents of every ``'...'`` pair in ``text``, in order.

    Equivalent to finding every ``'([^']*)'`` match in ``text``: pairs are read
    left to right without escaping rules, so an empty pair contributes an empty string
    and a doubled quote (``'a''b'``) reads as two values, not one. A final
    unterminated quote is ignored.
    """
    values: List[str] = []
    cursor = 0
    while True:
        open_at = text.find("'", cursor)
        if open_at < 0:
            return values
        close_at = text.find("'", open_at + 1)
        if close_at < 0:
            return values
        values.append(text[open_at + 1 : close_at])
        cursor = close_at + 1


__all__ = [
    "digit_runs",
    "digits_after_marker",
    "leading_ascii_uppercase",
    "leading_word",
    "leading_word_matches",
    "parenthesized",
    "parenthesized_number",
    "single_quoted",
    "word_after",
    "word_run",
]
