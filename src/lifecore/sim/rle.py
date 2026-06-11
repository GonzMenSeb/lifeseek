"""Strict RLE (Run-Length Encoded) reader/writer for :class:`Pattern` (Task 1.1).

Engine stdout and catalog files are *untrusted* (SPEC §10), so the parser is
deliberately strict: it accepts the standard RLE grammar and raises
``RLEParseError`` on anything malformed rather than guessing. ``to_rle`` emits a
canonical, header-tagged encoding of the normalized pattern.
"""

from __future__ import annotations

import re

from lifecore.sim.pattern import DEFAULT_RULE, Pattern

_HEADER_RE = re.compile(
    r"^\s*x\s*=\s*\d+\s*,\s*y\s*=\s*\d+\s*(?:,\s*rule\s*=\s*(?P<rule>[^\s,]+))?\s*$",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"(\d*)([bo$!])")
_LINE_WIDTH = 70


class RLEParseError(ValueError):
    """Raised when RLE text does not conform to the grammar."""


def parse_rle(text: str, rule: str | None = None) -> Pattern:
    """Parse RLE ``text`` into a :class:`Pattern`.

    Rule precedence: explicit ``rule`` arg > ``rule=`` in the header > ``DEFAULT_RULE``.
    Comment lines (``#...``) and the ``x = .., y = ..`` header are optional.
    """
    header_rule: str | None = None
    body_parts: list[str] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        header = _HEADER_RE.match(line)
        if header is not None and not body_parts:
            header_rule = header.group("rule")
            continue
        body_parts.append(line)

    body = "".join(body_parts)
    if "!" not in body:
        raise RLEParseError("RLE body missing terminating '!'")
    body = body.split("!", 1)[0] + "!"

    cells: set[tuple[int, int]] = set()
    x = 0
    y = 0
    pos = 0
    for match in _TOKEN_RE.finditer(body):
        if match.start() != pos:
            raise RLEParseError(f"unexpected character at offset {pos} in RLE body")
        pos = match.end()
        count_str, tag = match.groups()
        count = int(count_str) if count_str else 1
        if count == 0:
            raise RLEParseError("zero run-length is not allowed")
        if tag == "b":
            x += count
        elif tag == "o":
            for i in range(count):
                cells.add((x + i, y))
            x += count
        elif tag == "$":
            y += count
            x = 0
        elif tag == "!":
            break
    if pos != len(body):
        raise RLEParseError("trailing garbage after RLE terminator")

    chosen_rule = rule or header_rule or DEFAULT_RULE
    return Pattern(frozenset(cells), chosen_rule)


def to_rle(pattern: Pattern) -> str:
    """Encode ``pattern`` as canonical RLE with a header (normalized to the origin)."""
    p = pattern.normalize()
    width = p.width if not p.is_empty else 0
    height = p.height if not p.is_empty else 0
    header = f"x = {width}, y = {height}, rule = {p.rule}"

    if p.is_empty:
        return header + "\n!\n"

    rows: dict[int, set[int]] = {}
    for cx, cy in p.cells:
        rows.setdefault(cy, set()).add(cx)

    tokens: list[str] = []

    def emit(count: int, tag: str) -> None:
        tokens.append((str(count) if count > 1 else "") + tag)

    for y in range(height):
        if y > 0:
            # collapse consecutive blank rows into a single $ run
            if tokens and tokens[-1].endswith("$"):
                prev = tokens.pop()
                n = int(prev[:-1] or "1") + 1
                emit(n, "$")
            else:
                emit(1, "$")
        live = rows.get(y, set())
        if not live:
            continue
        last = max(live)
        run_tag: str | None = None
        run_len = 0
        for x in range(last + 1):
            tag = "o" if x in live else "b"
            if tag == run_tag:
                run_len += 1
            else:
                if run_tag is not None and not (run_tag == "b" and run_len == 0):
                    emit(run_len, run_tag)
                run_tag = tag
                run_len = 1
        if run_tag is not None:
            emit(run_len, run_tag)

    body = "".join(tokens) + "!"
    # wrap to <= 70 chars per line (standard), never splitting a <count><tag> token
    lines: list[str] = []
    line = ""
    for tok in re.findall(r"\d*[bo$!]", body):
        if len(line) + len(tok) > _LINE_WIDTH:
            lines.append(line)
            line = ""
        line += tok
    if line:
        lines.append(line)
    return header + "\n" + "\n".join(lines) + "\n"
