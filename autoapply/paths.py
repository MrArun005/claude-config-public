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
from pathlib import Path


def home() -> Path:
    """State root. Resolved per call, so a test can set the env var late."""
    return Path(os.environ.get("AUTOAPPLY_HOME") or (Path.home() / ".autoapply"))


def under(*parts: str) -> Path:
    return home().joinpath(*parts)
