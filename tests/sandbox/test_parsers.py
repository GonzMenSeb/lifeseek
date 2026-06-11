"""Fuzz + unit tests for the untrusted-output parsers (Task 6.2)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from lifecore.sandbox import parsers
from lifecore.sim.pattern import Pattern


def test_parse_apgcode_accepts_valid() -> None:
    for code in ("xs4_33", "xp2_7", "xq4_153", "xp15_4r4z4r4"):
        assert parsers.parse_apgcode(code) == code


def test_parse_apgcode_rejects_junk() -> None:
    for bad in ("", "hello", "xz4_33", "xs_33", "xs4", "4xs_33", "xs4 33", "'; DROP TABLE"):
        assert parsers.parse_apgcode(bad) is None


def test_parse_rle_safe_valid_and_invalid() -> None:
    assert parsers.parse_rle_safe("bob$2bo$3o!") is not None
    assert parsers.parse_rle_safe("not an rle at all") is None
    assert parsers.parse_rle_safe("99999z!") is None  # bad tag


def test_extract_patterns_from_noisy_stdout() -> None:
    stdout = (
        "qfind v2 starting...\n"
        "searching width 5\n"
        "x = 3, y = 3, rule = B3/S23\n"
        "bob$2bo$3o!\n"
        "done.\n"
    )
    pats = parsers.extract_patterns(stdout)
    assert len(pats) == 1
    assert pats[0].population == 5


def test_extract_patterns_empty_on_no_match() -> None:
    assert parsers.extract_patterns("no solution found\nUNSAT\n") == []


@settings(max_examples=400)
@given(st.text())
def test_fuzz_parse_rle_never_crashes(text: str) -> None:
    result = parsers.parse_rle_safe(text)
    assert result is None or isinstance(result, Pattern)


@settings(max_examples=400)
@given(st.text())
def test_fuzz_extract_patterns_never_crashes(text: str) -> None:
    out = parsers.extract_patterns(text)
    assert isinstance(out, list)
    assert all(isinstance(p, Pattern) for p in out)


@settings(max_examples=400)
@given(st.text())
def test_fuzz_parse_apgcode_never_crashes(text: str) -> None:
    out = parsers.parse_apgcode(text)
    assert out is None or out == text.strip()
