"""CLI subcommand tests (Task 11.1)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from lifecore.cli import discovery_id, load_campaign_yaml, main
from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.models import Oscillator

NOVEL = NoveltyResult(status=NoveltyStatus.NOVEL, apgcode="x")


def _osc_campaign() -> dict[str, object]:
    return {
        "spec": {"kind": "oscillator", "period": 2, "bbox_max": [3, 3], "rule": "B3/S23"},
        "engine_policy": ["rlifesrc", "lls"],
        "budget": {"max_engine_cpu_seconds": 100.0},
        "seed_candidates": ["3o!"],
    }


def _gun_campaign() -> dict[str, object]:
    return {"spec": {"kind": "gun", "bbox_max": [10, 10], "rule": "B3/S23"}}


def _write(path: Path, data: dict[str, object]) -> Path:
    path.write_text(yaml.safe_dump(data))
    return path


def test_load_campaign_yaml(tmp_path: Path) -> None:
    path = _write(tmp_path / "c.yaml", _osc_campaign())
    spec, budget, seeds = load_campaign_yaml(path)
    assert isinstance(spec, Oscillator)
    assert spec.period == 2
    assert budget.max_engine_cpu_seconds == 100.0
    assert seeds == ["3o!"]


def test_run_writes_report_and_discoveries(tmp_path: Path) -> None:
    campaign = _write(tmp_path / "c.yaml", _osc_campaign())
    out = tmp_path / "out"
    rc = main(["run", str(campaign), "--out", str(out)], novelty_fn=lambda p: NOVEL)
    assert rc == 0
    report = json.loads((out / "report.json").read_text())
    assert report["attempts"] == 1
    assert report["discoveries"] == 1
    artifacts = list((out / "discoveries").glob("*.json"))
    assert len(artifacts) == 1
    art = json.loads(artifacts[0].read_text())
    spec, _, _ = load_campaign_yaml(campaign)
    assert art["discovery_id"] == discovery_id(spec, parse_rle("3o!"))
    assert art["novelty"]["status"] == "NOVEL"
    assert art["verification"]["verdict"] == "PASS"


def test_run_no_capable_engine_returns_2(tmp_path: Path) -> None:
    campaign = _write(tmp_path / "gun.yaml", _gun_campaign())
    out = tmp_path / "out"
    rc = main(["run", str(campaign), "--out", str(out)], novelty_fn=lambda p: NOVEL)
    assert rc == 2
    report = json.loads((out / "report.json").read_text())
    assert report["no_capable_engine"] is True


def test_report_prints_baselines(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    campaign = _write(tmp_path / "c.yaml", _osc_campaign())
    out = tmp_path / "out"
    main(["run", str(campaign), "--out", str(out)], novelty_fn=lambda p: NOVEL)
    capsys.readouterr()
    rc = main(["report", str(out)], novelty_fn=lambda p: NOVEL)
    assert rc == 0
    printed = capsys.readouterr().out
    assert "baseline" in printed.lower()
    assert "iid" in printed.lower()
    assert "scs" in printed.lower()


def test_retarget_writes_new_yaml_with_new_spec(tmp_path: Path) -> None:
    campaign = _write(tmp_path / "c.yaml", _osc_campaign())
    new_spec = _write(
        tmp_path / "new.yaml",
        {"kind": "still_life", "bbox_max": [4, 4], "rule": "B3/S23"},
    )
    out = tmp_path / "retargeted.yaml"
    rc = main(["retarget", str(campaign), str(new_spec), "--out", str(out)])
    assert rc == 0
    old_spec, _, _ = load_campaign_yaml(campaign)
    new_campaign = yaml.safe_load(out.read_text())
    assert new_campaign["spec"]["kind"] == "still_life"
    # seed_candidates / budget carried over from the original campaign
    assert new_campaign["seed_candidates"] == ["3o!"]
    retargeted_spec, _, _ = load_campaign_yaml(out)
    assert retargeted_spec.spec_id != old_spec.spec_id
