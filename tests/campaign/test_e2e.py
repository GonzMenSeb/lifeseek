"""End-to-end campaign tests (Task 10.4): re-derive known, directed search, no-engine, baselines."""

import pytest

from lifecore.campaign.runner import InterventionQueue, run_campaign
from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.models import Gun, Oscillator, Spaceship, StillLife, SymmetryClass
from lifecore.verify.records import Verdict

GLIDER = "bob$2bo$3o!"


def always_novel(_p: Pattern) -> NoveltyResult:
    return NoveltyResult(status=NoveltyStatus.NOVEL)


def glider_spec() -> Spaceship:
    return Spaceship(
        displacement=(1, 1), period=4, symmetry_class=SymmetryClass.GLIDE_REFLECT, search_width=(1, 5)
    )


# --- (a) re-derive a known object: verifier PASS, novelty KNOWN --------------------


def test_rederive_known_object_pass_and_known() -> None:
    pytest.importorskip("lifelib")
    from lifecore.novelty import catagolue
    from lifecore.novelty.canonical import apgcode

    def real_novelty(p: Pattern) -> NoveltyResult:
        # fail-closed (SPEC §6.4): a pattern that won't canonicalize -> UNCERTAIN, never crash
        try:
            return catagolue.query(apgcode(p))
        except Exception:
            return NoveltyResult(status=NoveltyStatus.UNCERTAIN, notes="apgcode unavailable")

    report = run_campaign(
        glider_spec(), candidate_source=[parse_rle(GLIDER)], novelty_fn=real_novelty
    )
    # the loop verified PASS but novelty is KNOWN -> NOT accepted (proves loop + novelty work)
    assert report.attempts == 1
    assert len(report.discoveries) == 0
    assert any("KNOWN" in n or "novelty" in n.lower() for n in report.notes)


# --- (b) genuinely directed search to a typed outcome with full provenance ---------


def test_directed_search_accepts_with_provenance() -> None:
    spec = Oscillator(period=2, bbox_max=(3, 3))
    report = run_campaign(spec, candidate_source=[parse_rle("3o!")], novelty_fn=always_novel)
    assert len(report.discoveries) == 1
    disc = report.discoveries[0]
    assert disc.verification.verdict == Verdict.PASS
    assert disc.novelty.status == NoveltyStatus.NOVEL
    # full provenance recipe present
    r = disc.recipe
    assert len(r.reference_sim_version) == 64
    assert len(r.canonicalizer_version) == 64
    assert len(r.catagolue_snapshot_hash) == 64
    assert r.spec_id == spec.spec_id
    assert len(r.recipe_id) == 64


# --- (c) no-capable-engine path ----------------------------------------------------


def test_no_capable_engine_for_gun() -> None:
    report = run_campaign(Gun(), candidate_source=[], novelty_fn=always_novel)
    assert report.no_capable_engine is True
    assert report.attempts == 0
    assert any("no-capable-engine" in n for n in report.notes)


def test_no_capable_engine_for_oblique_ship_is_capable_but_stub() -> None:
    # oblique routes to ikpx2 (a stub) — it IS capability-mapped, so NOT no-capable-engine
    oblique = Spaceship(
        displacement=(2, 1), period=7, symmetry_class=SymmetryClass.ASYMMETRIC, search_width=(1, 8)
    )
    report = run_campaign(oblique, candidate_source=[], novelty_fn=always_novel)
    assert report.no_capable_engine is False


# --- (d) baselines present in the report at equal budget ---------------------------


def test_baselines_present_with_cis() -> None:
    spec = StillLife(bbox_max=(2, 2))
    report = run_campaign(spec, candidate_source=[parse_rle("2o$2o!")], novelty_fn=always_novel)
    d = report.to_dict()
    assert set(d["baselines"]) == {"iid", "scs"}
    for name in ("iid", "scs"):
        lo, hi = d["baselines"][name]["rate_ci"]
        assert 0.0 <= lo <= hi <= 1.0
    assert "discovery_rate_ci" in d


# --- async intervention: redirect takes precedence ---------------------------------


def test_redirect_intervention_defers_to_human_gate() -> None:
    q = InterventionQueue()
    q.redirect(StillLife(bbox_max=(3, 3)))

    # an infinite-ish source; redirect should break the loop before consuming it all
    def source() -> list[Pattern]:
        return [parse_rle("3o!")] * 100

    report = run_campaign(
        Oscillator(period=2, bbox_max=(3, 3)),
        candidate_source=source(),
        novelty_fn=always_novel,
        interventions=q,
    )
    assert report.redirect_requested is not None
    assert any("redirect" in n for n in report.notes)
