"""Sandbox runner tests (Task 6.2). Bubblewrap-dependent tests skip if absent."""

import pytest

from lifecore.engines.base import EngineBudget
from lifecore.sandbox import runner


def test_bwrap_argv_isolates_network_and_workdir() -> None:
    argv = runner.build_bwrap_argv(["/bin/echo", "hi"], "/work")
    assert argv[0] == "bwrap"
    assert "--unshare-net" in argv  # no network
    assert "--die-with-parent" in argv
    assert "--chdir" in argv and "/work" in argv
    # the inner command sits after the '--' separator
    assert argv[argv.index("--") + 1 :] == ["/bin/echo", "hi"]


@pytest.mark.skipif(not runner.sandbox_available(), reason="bubblewrap not installed")
def test_runs_command_and_captures_stdout() -> None:
    res = runner.run_sandboxed(["/bin/echo", "sandbox-ok"], budget=EngineBudget(wall_seconds=10))
    assert res.timed_out is False
    assert res.returncode == 0
    assert "sandbox-ok" in res.stdout


@pytest.mark.skipif(not runner.sandbox_available(), reason="bubblewrap not installed")
def test_writes_files_into_sandbox() -> None:
    res = runner.run_sandboxed(
        ["/bin/cat", "in.txt"], budget=EngineBudget(wall_seconds=10), files={"in.txt": "payload"}
    )
    assert "payload" in res.stdout


@pytest.mark.skipif(not runner.sandbox_available(), reason="bubblewrap not installed")
def test_wall_timeout_marks_timed_out_not_unsat() -> None:
    res = runner.run_sandboxed(["/bin/sleep", "5"], budget=EngineBudget(wall_seconds=1))
    assert res.timed_out is True  # a timeout is a timeout, never evidence of non-existence


def test_unavailable_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "sandbox_available", lambda: False)
    with pytest.raises(runner.SandboxUnavailable):
        runner.run_sandboxed(["/bin/echo", "x"])
