"""``lifeseek`` command-line interface (Task 11.1, SPEC §14.7).

A thin, deterministic driver over the OSS core: it loads a campaign description from
YAML, runs the LLM-free :func:`run_campaign` loop, and writes a content-addressed
report plus one artifact per accepted discovery. ``report`` pretty-prints a finished
run; ``retarget`` performs the human-approved re-aim (a YAML edit, **zero code
change**, SPEC §14.7); ``reproduce`` replays an accepted discovery bit-for-bit.

Campaign YAML format
--------------------
::

    spec:                      # a TargetSpec block (kind + fields)
      kind: oscillator
      period: 2
      bbox_max: [3, 3]
      rule: B3/S23
    engine_policy: [rlifesrc, lls]            # optional; informational only
    budget: {max_engine_cpu_seconds: 100.0}   # optional -> BudgetLimits(**budget)
    seed_candidates: ["3o!"]                   # optional, see below

``seed_candidates`` is a v1 **stand-in for sandboxed engine output**: external engine
binaries (rlifesrc/LLS/qfind/ikpx2) are absent in this build, so the campaign's
candidate stream is seeded from this optional list of RLE strings. In production these
candidates come from sandboxed engine adapters; the orchestrator is identical either
way (it never self-certifies — acceptance is always the gate's).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from lifecore.campaign.budget import BudgetLimits
from lifecore.campaign.runner import AcceptedDiscovery, run_campaign
from lifecore.novelty.oracle import novelty_query
from lifecore.novelty.results import NoveltyResult
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle, to_rle
from lifecore.targetspec.hashing import canonical_json
from lifecore.targetspec.models import TargetSpec
from lifecore.targetspec.yaml_io import from_yaml, to_yaml

NoveltyFn = Callable[[Pattern], NoveltyResult]


# --- campaign loading --------------------------------------------------------------
def load_campaign_yaml(path: str | Path) -> tuple[TargetSpec, BudgetLimits, list[str]]:
    """Load a campaign YAML into ``(spec, budget_limits, seed_candidates)``."""
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict) or "spec" not in data:
        raise ValueError("campaign YAML must be a mapping with a 'spec' block")
    spec = from_yaml(yaml.safe_dump(data["spec"]))
    budget = BudgetLimits(**data.get("budget", {}))
    seed_candidates = list(data.get("seed_candidates", []))
    return spec, budget, seed_candidates


# --- discovery artifacts -----------------------------------------------------------
def discovery_id(spec: TargetSpec, pattern: Pattern) -> str:
    """Stable id: ``<spec_id[:12]>-<sha256(canonical RLE)[:12]>``."""
    rle = to_rle(pattern)
    digest = hashlib.sha256(canonical_json(rle).encode("utf-8")).hexdigest()
    return f"{spec.spec_id[:12]}-{digest[:12]}"


def discovery_artifact(spec: TargetSpec, discovery: AcceptedDiscovery) -> dict[str, Any]:
    """Self-contained, replayable record of one accepted discovery."""
    return {
        "discovery_id": discovery_id(spec, discovery.pattern),
        "spec_yaml": to_yaml(spec),
        "candidate_rle": to_rle(discovery.pattern),
        "verification": discovery.verification.model_dump(mode="json"),
        "novelty": discovery.novelty.model_dump(mode="json"),
        "recipe": discovery.recipe.model_dump(mode="json"),
    }


# --- subcommands -------------------------------------------------------------------
def _cmd_run(args: argparse.Namespace, novelty_fn: NoveltyFn) -> int:
    spec, budget, seed_candidates = load_campaign_yaml(args.campaign)
    candidate_source = [parse_rle(rle) for rle in seed_candidates]
    report = run_campaign(
        spec,
        candidate_source=candidate_source,
        novelty_fn=novelty_fn,
        budget_limits=budget,
        baseline_seed=args.seed,
    )

    out_dir = Path(args.out) if args.out else Path("runs") / spec.spec_id[:12]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True))

    disc_dir = out_dir / "discoveries"
    if report.discoveries:
        disc_dir.mkdir(parents=True, exist_ok=True)
    for discovery in report.discoveries:
        artifact = discovery_artifact(spec, discovery)
        (disc_dir / f"{artifact['discovery_id']}.json").write_text(
            json.dumps(artifact, indent=2, sort_keys=True)
        )

    rates = " ".join(
        f"{name}={b.discovery_rate:.3f}" for name, b in sorted(report.baselines.items())
    )
    print(
        f"spec_id={spec.spec_id[:12]} attempts={report.attempts} "
        f"discoveries={len(report.discoveries)} "
        f"no_capable_engine={report.no_capable_engine} baselines[{rates}] -> {out_dir}"
    )
    return 2 if report.no_capable_engine else 0


def _cmd_report(args: argparse.Namespace) -> int:
    report = json.loads((Path(args.run_dir) / "report.json").read_text())
    lo, hi = report["discovery_rate_ci"]
    print(f"spec_id: {report['spec_id'][:12]}")
    print(f"attempts: {report['attempts']}")
    print(f"discoveries: {report['discoveries']}  (rate CI [{lo:.3f}, {hi:.3f}])")
    print(f"no_capable_engine: {report['no_capable_engine']}")
    print("baselines:")
    for name, b in sorted(report["baselines"].items()):
        clo, chi = b["rate_ci"]
        print(
            f"  {name}: {b['discoveries']}/{b['attempts']} "
            f"rate={b['rate']:.3f} CI [{clo:.3f}, {chi:.3f}]"
        )
    disc_dir = Path(args.run_dir) / "discoveries"
    if disc_dir.is_dir():
        for artifact_path in sorted(disc_dir.glob("*.json")):
            art = json.loads(artifact_path.read_text())
            print(f"  discovery {art['discovery_id']}: novelty={art['novelty']['status']}")
    for note in report["notes"]:
        print(f"  note: {note}")
    return 0


def _cmd_retarget(args: argparse.Namespace) -> int:
    data = yaml.safe_load(Path(args.campaign).read_text())
    if not isinstance(data, dict) or "spec" not in data:
        raise ValueError("campaign YAML must be a mapping with a 'spec' block")
    old_spec = from_yaml(yaml.safe_dump(data["spec"]))
    new_spec = from_yaml(Path(args.new_spec).read_text())

    data["spec"] = new_spec.canonical_payload()
    out_path = Path(args.out) if args.out else Path(f"{args.campaign}.retargeted.yaml")
    out_path.write_text(yaml.safe_dump(data, sort_keys=True))

    print(f"from_spec_id {old_spec.spec_id} -> to_spec_id {new_spec.spec_id}")
    return 0


def _cmd_reproduce(args: argparse.Namespace, novelty_fn: NoveltyFn) -> int:
    from lifecore.campaign.reproduce import reproduce_discovery

    artifact = json.loads(Path(args.artifact).read_text())
    result = reproduce_discovery(artifact, novelty_fn=novelty_fn)
    if result.ok:
        print(f"OK: {artifact['discovery_id']} reproduced bitwise")
        return 0
    print(f"MISMATCH: {artifact['discovery_id']}: {result.details}")
    return 1


# --- entrypoint --------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lifeseek", description="Directed GoL discovery harness.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run a campaign from a YAML description")
    p_run.add_argument("campaign", help="path to the campaign YAML")
    p_run.add_argument("--out", default=None, help="output run directory")
    p_run.add_argument("--seed", type=int, default=0, help="baseline seed")

    p_report = sub.add_parser("report", help="pretty-print a finished run")
    p_report.add_argument("run_dir", help="run directory holding report.json")

    p_retarget = sub.add_parser("retarget", help="re-aim a campaign onto a new spec (YAML edit)")
    p_retarget.add_argument("campaign", help="path to the existing campaign YAML")
    p_retarget.add_argument("new_spec", help="path to the new TargetSpec YAML")
    p_retarget.add_argument("--out", default=None, help="output campaign YAML path")

    p_repro = sub.add_parser("reproduce", help="bitwise-replay an accepted discovery artifact")
    p_repro.add_argument("artifact", help="path to a discovery artifact JSON")

    return parser


def main(argv: list[str] | None = None, *, novelty_fn: NoveltyFn | None = None) -> int:
    """Console entrypoint. ``novelty_fn`` defaults to the real fail-closed oracle.

    Tests inject a deterministic ``novelty_fn`` so the pipeline runs without lifelib.
    """
    fn: NoveltyFn = novelty_fn if novelty_fn is not None else novelty_query
    args = _build_parser().parse_args(argv)

    if args.command == "run":
        return _cmd_run(args, fn)
    if args.command == "report":
        return _cmd_report(args)
    if args.command == "retarget":
        return _cmd_retarget(args)
    if args.command == "reproduce":
        return _cmd_reproduce(args, fn)
    raise AssertionError(f"unhandled command {args.command!r}")  # pragma: no cover
