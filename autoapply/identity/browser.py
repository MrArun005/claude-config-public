"""
identity/browser.py — P1: the persistent identity layer.

Hard constraints (from the v2 plan — do not relax):
  * Dedicated user_data_dir. NEVER the real Chrome profile (Chrome >=136
    refuses CDP on the default dir anyway).
  * Single-writer: lockfile check, fail loudly, never corrupt.
  * Profile holds live session credentials: chmod 700, never sync/commit.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import paths

from playwright.async_api import async_playwright

PROFILE = paths.under("chrome-profile")
LOCK = PROFILE.parent / "chrome-profile.lock"


def _acquire_lock() -> None:
    PROFILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        pid = LOCK.read_text().strip()
        alive = False
        if pid.isdigit():
            try:
                os.kill(int(pid), 0)
                alive = True
            except (ProcessLookupError, PermissionError):
                alive = False
        if alive:
            sys.exit(
                f"FATAL: profile in use by pid {pid} (or a Chrome window is "
                f"open on {PROFILE}). Close it, or remove {LOCK} if stale."
            )
        LOCK.unlink()  # stale lock from a crashed run
    LOCK.write_text(str(os.getpid()))


def _release_lock() -> None:
    if LOCK.exists() and LOCK.read_text().strip() == str(os.getpid()):
        LOCK.unlink()


def _headless(default: bool) -> bool:
    """$AUTOAPPLY_HEADLESS overrides the caller, for CI and for debugging."""
    raw = os.environ.get("AUTOAPPLY_HEADLESS")
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "")


async def open_context(headless: bool = True):
    """Returns (playwright, context). Caller must call close_context()."""
    _acquire_lock()
    PROFILE.mkdir(parents=True, exist_ok=True)
    os.chmod(PROFILE, 0o700)
    pw = await async_playwright().start()

    # Default: system Chrome, nothing downloaded. $AUTOAPPLY_CHROME_PATH points
    # at an explicit binary instead — needed wherever no system Chrome exists,
    # or where the installed Playwright expects a different bundled revision
    # than the one on disk (then `channel` must be dropped, not just overridden).
    launch: dict = {
        "user_data_dir": str(PROFILE),
        "headless": _headless(headless),
        "viewport": {"width": 1440, "height": 900},
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if exe := os.environ.get("AUTOAPPLY_CHROME_PATH"):
        launch["executable_path"] = exe
    else:
        launch["channel"] = "chrome"

    try:
        ctx = await pw.chromium.launch_persistent_context(**launch)
    except Exception:
        _release_lock()
        await pw.stop()
        raise
    return pw, ctx


async def close_context(pw, ctx) -> None:
    try:
        await ctx.close()
        await pw.stop()
    finally:
        _release_lock()
