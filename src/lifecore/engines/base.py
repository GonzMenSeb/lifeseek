"""Engine adapter contract (Task 6.1, SPEC §4.3).

Every directed solver (qfind, rlifesrc, LLS, ikpx2) is wrapped behind this ABC so the
campaign layer treats them uniformly. Two invariants matter most:

* ``TIMEOUT`` and ``UNSAT`` are DISTINCT typed outcomes — a timeout is never evidence
  of non-existence (the width-escalation policy must not misread it).
* ``run`` is sandboxed and must NEVER raise on UNSAT/TIMEOUT — it returns a typed
  ``RawResult``. Engine stdout is untrusted and only becomes a Pattern via ``parse``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from lifecore.sim.pattern import Pattern
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import TargetSpec


class EngineOutcome(StrEnum):
    FOUND = "FOUND"
    UNSAT = "UNSAT"  # proven no solution in the posed problem (NOT a timeout)
    TIMEOUT = "TIMEOUT"  # ran out of budget; says nothing about existence
    ERROR = "ERROR"
    NO_CAPABILITY = "NO_CAPABILITY"


class NoCapability(Exception):
    """Raised by ``build_input`` when an engine cannot express the given spec."""


@dataclass(frozen=True)
class EngineBudget:
    """Resource ceiling for a single engine invocation."""

    cpu_seconds: float = 30.0
    wall_seconds: float = 60.0
    memory_mb: int = 2048


@dataclass(frozen=True)
class CapabilitySet:
    """The engines a given spec is routed to, derived from the central capability map."""

    engine_id: EngineId

    def handles(self, spec: TargetSpec) -> bool:
        from lifecore.targetspec.capability import capable_engines

        return self.engine_id in capable_engines(spec)


@dataclass(frozen=True)
class EngineConfig:
    """Fully-resolved, sandbox-ready invocation produced by ``build_input``."""

    engine_id: EngineId
    argv: list[str]
    stdin: str = ""
    files: dict[str, str] = field(default_factory=dict)  # filename -> contents (written in sandbox)
    budget: EngineBudget = field(default_factory=EngineBudget)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawResult:
    """Untrusted raw output of a sandboxed engine run (SPEC §4.3)."""

    outcome: EngineOutcome
    patterns_rle: list[str] = field(default_factory=list)
    stderr: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Candidate:
    """A parsed, structurally-valid candidate pattern with its provenance."""

    pattern: Pattern
    engine_id: EngineId
    meta: dict[str, Any] = field(default_factory=dict)


class EngineAdapter(ABC):
    """Uniform interface over an external Life search engine."""

    id: EngineId

    @abstractmethod
    def capabilities(self) -> CapabilitySet: ...

    @abstractmethod
    def build_input(self, spec: TargetSpec, budget: EngineBudget) -> EngineConfig:
        """Translate a spec into a concrete invocation. Raises :class:`NoCapability`."""
        ...

    @abstractmethod
    def run(self, cfg: EngineConfig) -> RawResult:
        """Run sandboxed. Returns a typed outcome; NEVER raises on UNSAT/TIMEOUT."""
        ...

    @abstractmethod
    def parse(self, raw: RawResult) -> list[Candidate]:
        """Parse untrusted engine output into candidates (fuzz-tested, never crashes)."""
        ...
