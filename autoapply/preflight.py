"""preflight.py — will this work on THIS machine? Run before the first real run.

    python preflight.py

Every check that can only be answered on your machine is answered here, so the
first real application fails in this script (cheap, reversible) rather than
halfway through a live ATS form (expensive, visible to an employer).

Checks: Python version, playwright, a launchable Chrome, the profile directory
and its lock, the answer bank and its coverage, the résumé file actually
existing, the why.j2 template actually rendering, the alias table parsing, the
ledger being writable, and the OTP secrets if you use an OTP platform.

Exit 0 = ready. Exit 1 = something listed below must be fixed first.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

OK, WARN, BAD = "ok  ", "warn", "FAIL"
rows: list[tuple[str, str, str]] = []


def record(level: str, name: str, detail: str = "") -> None:
    rows.append((level, name, detail))


def hard_failures() -> list[tuple[str, str, str]]:
    return [r for r in rows if r[0] == BAD]


# --------------------------------------------------------------------------
def check_python() -> None:
    v = sys.version_info
    # The codebase uses PEP 604 unions (`str | None`) at runtime in dataclasses.
    if (v.major, v.minor) >= (3, 10):
        record(OK, "python", f"{v.major}.{v.minor}.{v.micro}")
    else:
        record(BAD, "python", f"{v.major}.{v.minor} — need 3.10+ for `X | None`")


def check_imports() -> None:
    for mod, why in (("playwright", "browser automation"),
                     ("yaml", "answer bank"),
                     ("jinja2", "TEMPLATE answers")):
        try:
            __import__(mod)
            record(OK, f"import {mod}", why)
        except ImportError:
            record(BAD, f"import {mod}",
                   f"missing ({why}) — pip install -r requirements.txt")


def check_paths_and_profile() -> None:
    import paths
    from identity import browser

    home = paths.home()
    try:
        home.mkdir(parents=True, exist_ok=True)
        probe = home / ".preflight-write-probe"
        probe.write_text("x")
        probe.unlink()
        record(OK, "state dir writable", str(home))
    except OSError as exc:
        record(BAD, "state dir writable", f"{home}: {exc}")
        return

    mode = oct(home.stat().st_mode & 0o777)
    if mode != "0o700":
        record(WARN, "state dir permissions",
               f"{mode} — the profile holds live session cookies; chmod 700 {home}")
    else:
        record(OK, "state dir permissions", mode)

    if browser.LOCK.exists():
        pid = browser.LOCK.read_text().strip()
        alive = False
        if pid.isdigit():
            try:
                os.kill(int(pid), 0)
                alive = True
            except (ProcessLookupError, PermissionError):
                alive = False
        if alive:
            record(BAD, "profile lock",
                   f"held by pid {pid} — close that run or the Chrome window")
        else:
            record(WARN, "profile lock",
                   f"stale lock from pid {pid}; delete {browser.LOCK}")
    else:
        record(OK, "profile lock", "free")


async def check_chrome() -> None:
    """The check that matters most, because it is machine-specific."""
    from identity import browser
    try:
        pw, ctx = await browser.open_context(headless=True)
    except Exception as exc:
        msg = str(exc).split("\n")[0][:160]
        hint = ""
        if "channel" in msg.lower() or "executable" in msg.lower():
            hint = (" — set AUTOAPPLY_CHROME_PATH to your Chrome/Chromium binary, "
                    "or install Google Chrome")
        record(BAD, "chrome launches", f"{msg}{hint}")
        return
    try:
        page = await ctx.new_page()
        await page.set_content("<form><input name=probe></form>")
        from apply.fields import discover
        found = await discover(page)
        record(OK, "chrome launches",
               f"discovered {len(found)} field(s) on a probe page")
    except Exception as exc:
        record(BAD, "chrome usable", str(exc)[:160])
    finally:
        await browser.close_context(pw, ctx)


def check_bank() -> None:
    from state.answers import BANK, AnswerBank, is_placeholder
    if not BANK.exists():
        record(BAD, "answer bank",
               f"{BANK} missing — cp state/answers.example.yaml state/answers.yaml")
        return
    bank = AnswerBank(BANK)
    stubs = [k for k, v in bank.data.items()
             if isinstance(v, dict) and v.get("sourced")
             and is_placeholder(v.get("value"))]
    if stubs:
        record(WARN, "answer bank",
               f"{len(bank.data)} keys, {len(stubs)} still placeholders "
               f"({', '.join(sorted(stubs)[:5])}) — these will park, not submit")
    else:
        record(OK, "answer bank", f"{len(bank.data)} keys, no placeholders")

    # The résumé is the single most common cause of a first-run park.
    entry = bank.data.get("resume_path") or {}
    raw = entry.get("value")
    if not raw:
        record(WARN, "résumé file", "resume_path not set — file inputs will park")
    else:
        p = Path(str(raw)).expanduser()
        if p.is_file():
            record(OK, "résumé file", f"{p} ({p.stat().st_size // 1024} KB)")
        else:
            record(BAD, "résumé file",
                   f"{p} does not exist on this machine — every form with an "
                   f"upload will park")


def check_template() -> None:
    from state.answers import BANK, AnswerBank
    from apply.templates import Unrenderable, render
    bank = AnswerBank(BANK) if BANK.exists() else None
    if bank is None:
        return
    path = bank.template_path("why_this_company")
    if path is None:
        record(OK, "why.j2", "no TEMPLATE answer configured")
        return
    try:
        out = render(path, {"company": "Example Corp", "role": "Senior Engineer"})
        record(OK, "why.j2", f"renders, {len(out.split())} words")
    except Unrenderable as exc:
        record(WARN, "why.j2", f"{exc} — forms asking this will park")


def check_aliases() -> None:
    try:
        from apply.aliases import DERIVED, _table
        by_name, by_label = _table()
        record(OK, "alias table",
               f"{len(by_name)} name rules, {len(by_label)} label rules")
    except Exception as exc:
        record(BAD, "alias table", str(exc)[:160])
        return
    try:
        import yaml
        from state.seed import all_questions
        keys = {q["feeds"] for q in all_questions()}
        tbl = yaml.safe_load((ROOT / "state" / "field-aliases.yaml").read_text())
        reach = set(tbl["by_name"].values()) | {r["key"] for r in tbl["by_label"]}
        orphans = keys - reach - set(DERIVED) - {"assessment_willing"}
        if orphans:
            record(WARN, "catalogue reachability",
                   f"unreachable keys: {', '.join(sorted(orphans))}")
        else:
            record(OK, "catalogue reachability", f"all {len(keys)} keys reachable")
    except Exception as exc:
        record(WARN, "catalogue reachability", str(exc)[:120])


def check_ledger() -> None:
    from state import ledger
    try:
        con = ledger.connect()
        n = con.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        con.close()
        record(OK, "ledger", f"writable, {n} application(s) recorded")
    except Exception as exc:
        record(BAD, "ledger", str(exc)[:160])


def check_otp() -> None:
    from identity.otp import SECRETS
    from identity.session import PLATFORMS
    if not PLATFORMS:
        record(OK, "otp secrets", "no OTP platforms registered")
        return
    if SECRETS.exists():
        text = SECRETS.read_text()
        have = all(k in text for k in ("GMAIL_USER", "GMAIL_APP_PASSWORD"))
        mode = oct(SECRETS.stat().st_mode & 0o777)
        if not have:
            record(WARN, "otp secrets",
                   f"{SECRETS} missing GMAIL_USER or GMAIL_APP_PASSWORD")
        elif mode != "0o600":
            record(WARN, "otp secrets", f"present but chmod {mode}; use 600")
        else:
            record(OK, "otp secrets", "present")
    else:
        record(WARN, "otp secrets",
               f"{SECRETS} missing — needed only for OTP logins "
               f"({', '.join(PLATFORMS)})")


async def main() -> int:
    check_python()
    check_imports()
    if hard_failures():
        report()
        return 1

    check_paths_and_profile()
    check_bank()
    check_template()
    check_aliases()
    check_ledger()
    check_otp()
    await check_chrome()
    return report()


def report() -> int:
    width = max(len(n) for _, n, _ in rows) + 2
    print()
    for level, name, detail in rows:
        print(f"  [{level}] {name:<{width}} {detail}")

    bad = hard_failures()
    warns = [r for r in rows if r[0] == WARN]
    print()
    if bad:
        print(f"NOT READY — {len(bad)} blocking problem(s):")
        for _, name, detail in bad:
            print(f"  - {name}: {detail}")
        print("\nFix those, then re-run: python preflight.py")
        return 1
    if warns:
        print(f"READY, with {len(warns)} warning(s). Anything warned about will "
              f"PARK for review rather than submit — which is safe, just slower.")
    else:
        print("READY. Nothing will park for environment reasons.")
    print("\nNext:  python -m apply.runner \"<apply-url>\" --company X --role Y --plan")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
