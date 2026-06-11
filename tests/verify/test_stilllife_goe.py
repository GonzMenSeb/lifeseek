"""Still-life stability + rigorous GoE/non-existence protocol (Task 3.3)."""

from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.models import StillLife
from lifecore.verify import verifier
from lifecore.verify.records import OrphanWitness, Verdict

BLOCK = "2o$2o!"
BLINKER = "3o!"


def test_block_is_stable() -> None:
    rec = verifier.verify(parse_rle(BLOCK), StillLife(bbox_max=(2, 2)))
    assert rec.verdict == Verdict.PASS
    assert rec.residual_cell_count == 0
    assert rec.claim == "still_life"


def test_blinker_is_not_a_still_life() -> None:
    rec = verifier.verify(parse_rle(BLINKER), StillLife(bbox_max=(3, 3)))
    assert rec.verdict == Verdict.REJECT


def test_population_range_postfilter_enforced() -> None:
    # block has population 4; ask for 5..9 -> spec-not-met -> REJECT
    rec = verifier.verify(parse_rle(BLOCK), StillLife(bbox_max=(2, 2), population_range=(5, 9)))
    assert rec.verdict == Verdict.REJECT


def test_goe_requires_orphan_witness() -> None:
    # No witness at all: cannot claim non-existence.
    rec = verifier.verify_nonexistence(None, rule="B3/S23")
    assert rec.verdict == Verdict.REJECT
    assert rec.claim == "nonexistence"


def test_smallbox_unsat_is_not_nonexistence() -> None:
    # A single small-box UNSAT: insufficient padding, no exhaustive proof -> REJECT.
    smallbox = OrphanWitness(
        orphan=parse_rle(BLOCK), padding_thickness=1, no_preimage_proof=False, source="smallbox"
    )
    rec = verifier.verify_nonexistence(smallbox, rule="B3/S23")
    assert rec.verdict == Verdict.REJECT


def test_valid_orphan_witness_accepts() -> None:
    witness = OrphanWitness(
        orphan=Pattern(frozenset({(0, 0), (2, 0), (4, 0), (1, 2)})),
        padding_thickness=4,
        no_preimage_proof=True,
        source="lls-sat-preimage",
    )
    rec = verifier.verify_nonexistence(witness, rule="B3/S23")
    assert rec.verdict == Verdict.PASS
    assert rec.signature_valid()


def test_insufficient_padding_rejected() -> None:
    witness = OrphanWitness(
        orphan=parse_rle(BLOCK), padding_thickness=3, no_preimage_proof=True, source="thin"
    )
    rec = verifier.verify_nonexistence(witness, rule="B3/S23")
    assert rec.verdict == Verdict.REJECT
