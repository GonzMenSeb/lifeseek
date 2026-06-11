"""Re-aim demo (Task 11.3, SPEC §14.7).

Proves a campaign is re-aimed by editing YAML alone: run an Oscillator p2 campaign,
``retarget`` it onto a StillLife spec, run the retargeted campaign, and assert both runs
produced reports with DIFFERENT spec_ids while NO source file under ``src/`` changed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from lifecore.cli import load_campaign_yaml, main
from lifecore.novelty.results import NoveltyResult, NoveltyStatus

NOVEL = NoveltyResult(status=NoveltyStatus.NOVEL, apgcode="x")

_SRC = Path(__file__).resolve().parents[2] / "src"


def _src_fingerprint() -> str:
    h = hashlib.sha256()
    for path in sorted(_SRC.rglob("*.py")):
        h.update(path.relative_to(_SRC).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def test_reaim_via_yaml_edit_no_code_change(tmp_path: Path) -> None:
    before = _src_fingerprint()

    campaign = tmp_path / "osc.yaml"
    campaign.write_text(
        yaml.safe_dump(
            {
                "spec": {"kind": "oscillator", "period": 2, "bbox_max": [3, 3], "rule": "B3/S23"},
                "seed_candidates": ["3o!"],
            }
        )
    )
    new_spec = tmp_path / "still.yaml"
    new_spec.write_text(
        yaml.safe_dump({"kind": "still_life", "bbox_max": [4, 4], "rule": "B3/S23"})
    )

    out1 = tmp_path / "run1"
    assert main(["run", str(campaign), "--out", str(out1)], novelty_fn=lambda p: NOVEL) == 0

    retargeted = tmp_path / "still.campaign.yaml"
    assert main(["retarget", str(campaign), str(new_spec), "--out", str(retargeted)]) == 0

    out2 = tmp_path / "run2"
    assert main(["run", str(retargeted), "--out", str(out2)], novelty_fn=lambda p: NOVEL) == 0

    report1 = json.loads((out1 / "report.json").read_text())
    report2 = json.loads((out2 / "report.json").read_text())

    assert report1["spec_id"] != report2["spec_id"]

    new_spec_obj, _, _ = load_campaign_yaml(retargeted)
    assert report2["spec_id"] == new_spec_obj.spec_id

    after = _src_fingerprint()
    assert before == after, "re-aim must change zero source files"
