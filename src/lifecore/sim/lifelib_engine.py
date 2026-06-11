"""Thin wrapper over python-lifelib — the HashLife *producer* backend (Task 1.3).

Role (SPEC §4.3): fast evolution + apgcode canonicalization + soup census. This is
NOT a directed search engine and NOT part of the verification trust path — the
verifier uses ``sim/reference.py`` only. lifelib is an optional extra; importing
this module without it raises a clear error, and dependent tests skip.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import to_rle


def _rule_to_lifelib(rule: str) -> str:
    """Map a ``Bxx/Sxx`` rulestring to lifelib's lowercase ``bxxsxx`` form."""
    return rule.replace("/", "").replace(" ", "").lower()


@lru_cache(maxsize=8)
def _lifetree(rule: str) -> Any:
    try:
        import lifelib
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "python-lifelib is required for the HashLife backend; install the 'lifelib' extra."
        ) from exc
    session = lifelib.load_rules(_rule_to_lifelib(rule))
    return session.lifetree(memory=1000, n_layers=1)


def _rle_body(pattern: Pattern) -> str:
    """Header-less RLE body for feeding lifelib's pattern parser."""
    lines = [ln for ln in to_rle(pattern).splitlines() if not ln.lower().startswith("x =")]
    return "".join(lines)


def _to_lifelib(pattern: Pattern) -> Any:
    return _lifetree(pattern.rule).pattern(_rle_body(pattern))


def _from_lifelib(lp: Any, rule: str, offset: tuple[int, int]) -> Pattern:
    ox, oy = offset
    coords = lp.coords()
    cells = frozenset((int(x) + ox, int(y) + oy) for x, y in coords.tolist())
    return Pattern(cells, rule)


def evolve(pattern: Pattern, n: int) -> Pattern:
    """Advance ``pattern`` by ``n`` generations via HashLife (absolute coords preserved)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0 or pattern.is_empty:
        return pattern
    xmin, ymin, _, _ = pattern.bbox
    advanced = _to_lifelib(pattern).advance(n)  # GoL is translation-equivariant
    return _from_lifelib(advanced, pattern.rule, (xmin, ymin))


def fast_forward(pattern: Pattern, big_n: int) -> Pattern:
    """Alias for :func:`evolve` — HashLife handles large ``n`` natively (no clipping)."""
    return evolve(pattern, big_n)


def apgcode(pattern: Pattern) -> str:
    """Canonical apgcode of ``pattern`` (phase/orientation/translation invariant)."""
    if pattern.is_empty:
        return "xs0_0"
    code = _to_lifelib(pattern).apgcode
    return str(code)
