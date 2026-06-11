"""Strict, fuzz-tested parsers for untrusted engine output (Task 6.2, SPEC §10).

Engine stdout and Catagolue responses are untrusted. These parsers are total: on ANY
malformed input they return ``None``/``[]`` rather than raising, and they NEVER emit an
invalid Pattern or apgcode. A hypothesis fuzz suite asserts these invariants.
"""

from __future__ import annotations

import re

from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import RLEParseError, parse_rle

# apgcode grammar: x{s|p|q}<population>_<base36 hash...>  (e.g. xs4_33, xp2_7, xq4_153).
_APGCODE_RE = re.compile(r"^x[spq][0-9]+_[0-9a-z][0-9a-z_]*$")

# An RLE body runs until the terminating '!'. We capture a candidate block ending in '!'.
_RLE_BLOCK_RE = re.compile(r"[bo0-9$\s]*!")


def parse_apgcode(text: str) -> str | None:
    """Return ``text`` if it is a syntactically valid apgcode, else ``None``."""
    candidate = text.strip()
    return candidate if _APGCODE_RE.match(candidate) else None


def parse_rle_safe(text: str, rule: str | None = None) -> Pattern | None:
    """Parse RLE, returning ``None`` on any malformation (never raises)."""
    try:
        return parse_rle(text, rule=rule)
    except (RLEParseError, ValueError, OverflowError, MemoryError):
        return None
    except Exception:  # totality guarantee: untrusted input must never crash the pipeline
        return None


def extract_patterns(stdout: str, rule: str | None = None) -> list[Pattern]:
    """Scan untrusted engine ``stdout`` for RLE blocks and return the ones that parse.

    Header lines (``x = .., y = ..``) are kept with their following body so a real RLE
    parses; junk between blocks is ignored. Empty results are normal (UNSAT/TIMEOUT).
    """
    patterns: list[Pattern] = []
    seen: set[frozenset[tuple[int, int]]] = set()
    for line_block in _candidate_blocks(stdout):
        p = parse_rle_safe(line_block, rule=rule)
        if p is not None and not p.is_empty and p.cells not in seen:
            seen.add(p.cells)
            patterns.append(p)
    return patterns


def _candidate_blocks(stdout: str) -> list[str]:
    """Split stdout into header+body candidate blocks ending at '!'."""
    blocks: list[str] = []
    lines = stdout.splitlines()
    buffer: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("x =") or _RLE_BLOCK_RE.fullmatch(stripped):
            buffer.append(line)
            if stripped.endswith("!"):
                blocks.append("\n".join(buffer))
                buffer = []
        else:
            buffer = []
    return blocks
