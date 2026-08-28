"""paths.py — one place that decides where state lives.

Every module used to hardcode `Path.home() / ".autoapply"`, which made the
test harness write into the real ledger, the real checkpoints and the real
Chrome profile. HOME is now overridable via $AUTOAPPLY_HOME so a run can be
pointed at a throwaway directory.

Nothing here creates directories: the owning module still decides when to
mkdir, so an import can never leave a stray tree behind.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def home() -> Path:
    """State root. Resolved per call, so a test can set the env var late."""
    return Path(os.environ.get("AUTOAPPLY_HOME") or (Path.home() / ".autoapply"))


def under(*parts: str) -> Path:
    return home().joinpath(*parts)


def init_console() -> None:
    """Make stdout/stderr survive non-ASCII on a Windows console.

    Windows defaults to cp1252, which cannot encode the arrows, em-dashes and
    accented characters this tool prints (and which real job-application forms
    are full of). Without this, printing a single character crashes the run --
    a batch died on job 1 of 12 for exactly that reason. errors="replace" keeps
    output legible rather than raising, on any console.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass          # already fine, or not reconfigurable
