"""Sandboxed process runner (Task 6.2, SPEC §10).

Wrapped engine binaries are untrusted: they run inside bubblewrap with NO network
(``--unshare-net``), a read-only view of the host, a writable scratch dir, and
``RLIMIT_CPU``/``RLIMIT_AS`` ceilings. A wall-clock timeout converts runaway searches
(incl. HashLife blow-ups) into a ``timed_out`` result the width-escalation policy
handles — a timeout is never read as proof of non-existence.

If bubblewrap is unavailable the runner refuses to pretend it sandboxed: callers must
check :func:`sandbox_available` and decide (engine adapters skip/limit accordingly).
All invocations use list argv (no shell) — engine output and config are untrusted.
"""

from __future__ import annotations

import resource
import shutil
import subprocess  # nosec B404 - list-argv only, never shell=True
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lifecore.engines.base import EngineBudget

BWRAP = "bwrap"


class SandboxUnavailable(RuntimeError):
    """Raised when no sandbox backend (bubblewrap) is available."""


def sandbox_available() -> bool:
    return shutil.which(BWRAP) is not None


@dataclass(frozen=True)
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


def build_bwrap_argv(inner_argv: list[str], workdir: str) -> list[str]:
    """Construct the bubblewrap wrapper argv: read-only host, writable workdir, no net."""
    return [
        BWRAP,
        "--ro-bind", "/", "/",
        "--dev", "/dev",
        "--proc", "/proc",
        "--tmpfs", "/tmp",
        "--bind", workdir, workdir,
        "--chdir", workdir,
        "--unshare-net",
        "--unshare-pid",
        "--unshare-ipc",
        "--die-with-parent",
        "--new-session",
        "--",
        *inner_argv,
    ]


def _rlimit_preexec(budget: EngineBudget) -> Callable[[], None]:
    cpu = max(1, int(budget.cpu_seconds))
    mem_bytes = max(64, budget.memory_mb) * 1024 * 1024

    def _apply() -> None:  # pragma: no cover - runs in the forked child
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

    return _apply


def run_sandboxed(
    inner_argv: list[str],
    *,
    budget: EngineBudget | None = None,
    files: dict[str, str] | None = None,
    stdin: str = "",
) -> SandboxResult:
    """Run ``inner_argv`` under bubblewrap with no network and resource ceilings.

    ``files`` (name -> contents) are written into the sandbox scratch dir before exec.
    Raises :class:`SandboxUnavailable` if bubblewrap is missing — never silently
    runs unsandboxed.
    """
    if not sandbox_available():
        raise SandboxUnavailable("bubblewrap (bwrap) is not installed")
    budget = budget or EngineBudget()

    with tempfile.TemporaryDirectory(prefix="lifeseek-sbx-") as workdir:
        for name, contents in (files or {}).items():
            (Path(workdir) / name).write_text(contents, encoding="utf-8")
        argv = build_bwrap_argv(inner_argv, workdir)
        try:
            proc = subprocess.run(  # nosec B603 - list argv, no shell, sandboxed by bwrap
                argv,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=budget.wall_seconds,
                preexec_fn=_rlimit_preexec(budget),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                returncode=-1,
                stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                timed_out=True,
            )
    return SandboxResult(
        returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, timed_out=False
    )
