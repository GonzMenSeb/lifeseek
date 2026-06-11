"""Shared run/parse plumbing for engine adapters (Tasks 6.3-6.6).

The mapping from a sandboxed process result to a typed :class:`EngineOutcome` is
identical in shape across every real adapter; only the binary name and the UNSAT
marker strings differ. Keeping it here makes ``run`` a tiny, testable call.

The sandbox primitives are passed in (not imported) so each adapter module owns its
own ``shutil`` / ``sandbox_available`` / ``run_sandboxed`` names — that keeps them
monkeypatchable per adapter in unit tests without the binaries present.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from lifecore.engines.base import Candidate, EngineConfig, EngineOutcome, RawResult
from lifecore.sandbox.parsers import extract_patterns
from lifecore.sandbox.runner import SandboxResult, SandboxUnavailable
from lifecore.targetspec.capability import EngineId


def run_engine(
    cfg: EngineConfig,
    *,
    binary: str,
    which: Callable[[str], str | None],
    sandbox_available: Callable[[], bool],
    run_sandboxed: Callable[..., SandboxResult],
    unsat_markers: Sequence[str],
    non_found_clean_exit: EngineOutcome,
) -> RawResult:
    """Execute ``cfg`` sandboxed and map the result to a typed outcome (never raises)."""
    if which(binary) is None:
        return RawResult(outcome=EngineOutcome.ERROR, meta={"reason": f"{binary} not installed"})
    if not sandbox_available():
        return RawResult(outcome=EngineOutcome.ERROR, meta={"reason": "sandbox unavailable"})

    try:
        res = run_sandboxed(cfg.argv, budget=cfg.budget, files=cfg.files, stdin=cfg.stdin)
    except (SandboxUnavailable, OSError) as exc:
        return RawResult(outcome=EngineOutcome.ERROR, meta={"reason": str(exc)})

    if res.timed_out:
        return RawResult(
            outcome=EngineOutcome.TIMEOUT, stderr=res.stderr, meta={"stdout": res.stdout}
        )

    meta = {"stdout": res.stdout}
    if extract_patterns(res.stdout):
        return RawResult(outcome=EngineOutcome.FOUND, stderr=res.stderr, meta=meta)

    blob = f"{res.stdout}\n{res.stderr}".lower()
    if any(marker.lower() in blob for marker in unsat_markers):
        return RawResult(outcome=EngineOutcome.UNSAT, stderr=res.stderr, meta=meta)

    return RawResult(outcome=non_found_clean_exit, stderr=res.stderr, meta=meta)


def parse_stdout(raw: RawResult, engine_id: EngineId) -> list[Candidate]:
    """Parse untrusted stdout into candidates (total; never raises)."""
    stdout = raw.meta.get("stdout", "")
    return [Candidate(pattern=p, engine_id=engine_id) for p in extract_patterns(stdout)]
