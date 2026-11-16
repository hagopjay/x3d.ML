"""Test bootstrap: find x3dtrace.py without installing it.

The tests live in <repo>/tests/ with the module in <repo>/src/. The first candidate that holds x3dtrace.py
wins; X3DTRACE_PATH (a directory holding x3dtrace.py) overrides.
"""
import json
import os
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _find_module_dir():
    cands = []
    if os.environ.get("X3DTRACE_PATH"):
        cands.append(Path(os.environ["X3DTRACE_PATH"]))
    cands += [HERE.parent / "src", HERE.parent.parent / "src", HERE.parent]
    for c in cands:
        if (c / "x3dtrace.py").is_file():
            return c
    raise RuntimeError("x3dtrace.py not found; tried: %s" % ", ".join(str(c) for c in cands))


MODULE_DIR = _find_module_dir()
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

PERF_LOG = {}


def pytest_configure(config):
    config.addinivalue_line("markers", "fixed(reason): regression test for a defect found by the independent review and since fixed")


@pytest.fixture(scope="session")
def module_dir():
    return MODULE_DIR


@pytest.fixture
def perf():
    """perf(name, seconds, **extra) records a timing; set X3DTRACE_PERF_LOG=<file> to have the session write them as JSON."""
    def rec(name, seconds, **extra):
        PERF_LOG[name] = dict(seconds=round(seconds, 4), **extra)
        print("PERF %s: %.3f s %s" % (name, seconds, extra or ""))
    return rec


def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("X3DTRACE_PERF_LOG")
    if PERF_LOG and out:
        try:
            Path(out).write_text(json.dumps(PERF_LOG, indent=1, sort_keys=True))
        except OSError:
            pass
