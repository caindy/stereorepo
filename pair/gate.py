# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6", "ruff==0.14.0"]
# ///
"""The pair loop's gate: its tests and ruff, reported in the one shape every gate here prints (A21).

Each test module under `pair/` is one step, and `ruff check` over `pair/` with
the repository's `.meta/ruff.toml` is the last. A step prints
`ok <step> — <scope>` when it passes, and `x  <step> (<count>)` with one
indented line per failure or finding when it does not. The exit code is
non-zero when any step failed.

The tests of a step run across worker processes, one per two CPUs unless
`PAIR_TEST_WORKERS` gives the count; `PAIR_TEST_WORKERS=1` runs them one after
another in a single worker. A test is handed out on its own unless its class or
module has fixtures (`setUpClass`, `tearDownClass`, `setUpModule`), which keep
the class or module together in one worker.

A worker is this script started again with `--worker`, fed one unit of test ids
per line on its stdin and answering one JSON line per unit. `multiprocessing`
is not used, because a seat's sandbox refuses the
`os.sysconf("SC_SEM_NSEMS_MAX")` call that its process pool makes before
starting any process.
"""

from __future__ import annotations

import io
import json
import os
import queue
import re
import subprocess
import sys
import threading
import unittest
from collections.abc import Iterator
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE.parent / ".meta" / "ruff.toml"

Problem = tuple[str, str]

FINDING = re.compile(r"^.+:\d+:\d+: ")
"""A finding in ruff's concise output: `path:line:col: CODE message`, or a syntax error."""


def workers() -> int:
    """The number of worker processes: `PAIR_TEST_WORKERS`, or one per two CPUs.

    One worker per CPU was slower and flaky. With 18 workers, each starting
    git processes, the run spent most of its time in the kernel. The
    stand-in `claude` in `ClaudeSeatTest` then sometimes took longer than
    10 s to start, and its turns timed out.
    """
    raw = os.environ.get("PAIR_TEST_WORKERS")
    if raw is None:
        return max(1, (os.cpu_count() or 1) // 2)
    if not raw.isdigit() or int(raw) < 1:
        raise SystemExit(f"PAIR_TEST_WORKERS must be a positive integer, not {raw!r}")  # noqa: TRY003  # reason: the message is all a person sees when the gate refuses the variable, so it stays where the variable is read
    return int(raw)


def cases(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    """Every test in a suite, with the nesting the loader adds taken away."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def units(module: str, suite: unittest.TestSuite) -> list[list[str]]:
    """The module's tests as units of work, each a list of test ids for one worker."""
    tests = list(cases(suite))
    if hasattr(sys.modules[module], "setUpModule"):
        return [[test.id() for test in tests]]
    together: dict[type, list[str]] = {}
    out: list[list[str]] = []
    for test in tests:
        cls = type(test)
        if (
            cls.setUpClass.__func__ is unittest.TestCase.setUpClass.__func__
            and cls.tearDownClass.__func__ is unittest.TestCase.tearDownClass.__func__
        ):
            out.append([test.id()])
        elif cls in together:
            together[cls].append(test.id())
        else:
            together[cls] = [test.id()]
            out.append(together[cls])
    return out


def run(ids: list[str]) -> tuple[int, list[Problem]]:
    """Run one unit: the count of tests run, and each failure's id and last line."""
    return report(unittest.defaultTestLoader.loadTestsFromNames(ids))


def report(suite: unittest.TestSuite) -> tuple[int, list[Problem]]:
    """Run a suite here: the count of tests run, and each failure's id and last line."""
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    problems = [
        (case.id(), trace.strip().splitlines()[-1])
        for case, trace in result.failures + result.errors
    ]
    return result.testsRun, problems


def worker() -> int:
    """Answer each unit read from stdin with one JSON line on the original stdout.

    File descriptor 1 is pointed at stderr first, so that nothing a test or its
    subprocesses print can be mistaken for an answer. File descriptor 0 is
    pointed at `/dev/null`, so that a subprocess reading stdin gets end of file,
    and does not wait forever on the open pipe or take the next unit.
    """
    answers = os.fdopen(os.dup(1), "w")
    requests = os.fdopen(os.dup(0), "r")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.close(null)
    sys.stdin = os.fdopen(0, "r", closefd=False)
    for line in requests:
        count, problems = run(json.loads(line))
        answers.write(json.dumps([count, problems]) + "\n")
        answers.flush()
    return 0


def spawn() -> subprocess.Popen[str]:
    """Start a worker process."""
    return subprocess.Popen(
        [sys.executable, __file__, "--worker"],
        cwd=HERE,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )


def step(module: str, count: int) -> tuple[int, list[Problem]]:  # noqa: C901  # reason: the driving thread is a closure over the queue, the lock and the tally it shares with the other threads
    """Run a module's units across `count` workers and add up what they report.

    A module that fails to import runs here instead: the loader stands in a
    test that reports why, and it has no id that a worker could load. Every
    unit appears in the result, either counted or as a problem. A unit held by
    a worker that dies, or by a thread that fails, or still queued after every
    thread has stopped, is reported as a problem rather than left out of the count.
    """
    suite = unittest.defaultTestLoader.loadTestsFromName(module)
    if module not in sys.modules:
        return report(suite)
    todo: queue.Queue[list[str]] = queue.Queue()
    for ids in units(module, suite):
        todo.put(ids)
    total, problems = 0, []
    lock = threading.Lock()

    def drive() -> None:
        nonlocal total
        ids: list[str] = []
        proc: subprocess.Popen[str] | None = None
        try:
            proc = spawn()
            while True:
                try:
                    ids = todo.get_nowait()
                except queue.Empty:
                    return
                assert proc.stdin and proc.stdout
                try:
                    proc.stdin.write(json.dumps(ids) + "\n")
                    proc.stdin.flush()
                    line = proc.stdout.readline()
                except BrokenPipeError:
                    line = ""
                if not line:
                    with lock:
                        problems.append((", ".join(ids), "a worker died before reporting"))
                    proc.kill()
                    proc.wait()
                    proc = spawn()
                    continue
                ran, found = json.loads(line)
                with lock:
                    total += ran
                    problems.extend((case, last) for case, last in found)
                ids = []
        except Exception as error:  # noqa: BLE001  # reason: whatever a driving thread raises becomes a reported problem, so no unit drops out of the count
            with lock:
                problems.append((", ".join(ids) or "a worker", f"the gate failed: {error!r}"))
        finally:
            if proc is not None:
                if proc.stdin:
                    proc.stdin.close()
                proc.wait()

    threads = [threading.Thread(target=drive) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    while not todo.empty():
        problems.append((", ".join(todo.get_nowait()), "no worker was left to run it"))
    return total, sorted(problems)


def lint(directory: Path = HERE) -> tuple[bool, list[str]]:
    """Run `ruff check` over `directory` with `CONFIG`: whether it passed, and the lines to print.

    The lines are `ok ruff — <directory>`, or `x  ruff (<count>)` followed by
    one indented line per finding. A run in which ruff itself fails, such as
    an unreadable configuration or a ruff that cannot be imported, is a
    failure with its error as the one line, not a step that could not run:
    ruff is a dependency of this script, so a missing one is the gate's fault.
    `--no-cache` keeps ruff from writing `.ruff_cache/` into the checkout.
    """
    done = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format", "concise",
         "--config", str(CONFIG), str(directory)],
        check=False,
        capture_output=True,
        text=True,
    )
    if done.returncode == 0:
        return True, [f"ok ruff — {directory.name}/"]
    findings = [line for line in done.stdout.splitlines() if FINDING.match(line)]
    if done.returncode != 1 or not findings:
        said = (done.stderr.strip() or done.stdout.strip()).splitlines()
        findings = [said[-1] if said else f"ruff exited {done.returncode} and said nothing"]
    return False, [f"x  ruff ({len(findings)})", *(f"     {line}" for line in findings)]


def main() -> int:
    """Run each test module as a step, then ruff, and print each verdict."""
    sys.path.insert(0, str(HERE))
    if sys.argv[1:] == ["--worker"]:
        return worker()
    count = workers()
    failed = False
    for path in sorted(HERE.glob("test_*.py")):
        ran, problems = step(path.stem, count)
        name = f"{path.stem.removeprefix('test_')} tests"
        if problems:
            failed = True
            print(f"x  {name} ({len(problems)})")
            for case, last in problems:
                print(f"     {case}: {last}")
        else:
            print(f"ok {name} — {ran} tests")
    passed, lines = lint()
    print("\n".join(lines))
    failed = failed or not passed
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
