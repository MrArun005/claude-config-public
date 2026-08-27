"""identity/bootstrap.py — the headed last resort.

identity/session.py already tells the user to run this:

    raise RuntimeError(
        f"{platform.name}: automated re-login failed — run headed bootstrap:\\n"
        f"  python -m identity.bootstrap {platform.name}"
    )

…but the module did not exist, so that escalation dead-ended. This is it.

Opens a visible browser on the persistent profile and waits while you log in by
hand. Because the profile is the same `user_data_dir` every automated run uses,
the cookies you create here are the cookies those runs inherit — that is the
entire point of the persistent identity layer (P1). Expected frequency is about
monthly per platform, when the session cookie finally expires and the automated
email-OTP path in session.relogin() cannot recover it.

    python -m identity.bootstrap proxify
    python -m identity.bootstrap --list
    python -m identity.bootstrap --url https://example.com/login
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from . import browser
from .session import PLATFORMS, Platform, session_alive


async def bootstrap(platform: Platform | None, url: str | None,
                    timeout_s: int) -> int:
    target = url or (platform.login_url or platform.account_url if platform else None)
    if not target:
        print("nothing to open: give a platform name or --url", file=sys.stderr)
        return 2

    # Headless would defeat the purpose: a human has to see and use this window.
    pw, ctx = await browser.open_context(headless=False)
    try:
        page = await ctx.new_page()
        await page.goto(target, wait_until="domcontentloaded")

        print(f"\nA browser window is open on {target}")
        print(f"Profile: {browser.PROFILE}")
        print("\nLog in by hand — solve whatever the automated path could not")
        print("(captcha, device confirmation, a new consent screen).")

        if platform is None:
            input("\nPress Enter here when you are done… ")
            print("Saved into the persistent profile.")
            return 0

        print(f"\nWaiting up to {timeout_s}s for the session to go live; "
              f"polling `{platform.login_selector}` on {platform.account_url}.")
        deadline = asyncio.get_running_loop().time() + timeout_s
        while asyncio.get_running_loop().time() < deadline:
            if await session_alive(ctx, platform):
                print(f"\n{platform.name}: session is live and saved to the profile.")
                print("Automated runs will now reuse it until it expires.")
                return 0
            await asyncio.sleep(3)

        print(f"\n{platform.name}: still logged out after {timeout_s}s.",
              file=sys.stderr)
        print("If you did log in, the selector may be wrong — the entries in "
              "identity/session.py PLATFORMS are marked '# verify'.",
              file=sys.stderr)
        return 1
    finally:
        await browser.close_context(pw, ctx)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m identity.bootstrap",
        description="Headed human login into the persistent profile "
                    "(last resort after session.relogin() fails).")
    ap.add_argument("platform", nargs="?", help=f"one of: {', '.join(PLATFORMS)}")
    ap.add_argument("--url", help="open this URL instead of a registered platform")
    ap.add_argument("--timeout", type=int, default=300,
                    help="seconds to wait for the session to go live (default 300)")
    ap.add_argument("--list", action="store_true", help="list registered platforms")
    args = ap.parse_args(argv)

    if args.list:
        for name, plat in PLATFORMS.items():
            print(f"{name:12} {plat.login_url or plat.account_url}")
        return 0

    if not args.platform and not args.url:
        ap.error("give a platform name or --url (see --list)")

    plat = None
    if args.platform:
        plat = PLATFORMS.get(args.platform)
        if plat is None:
            print(f"unknown platform {args.platform!r}; "
                  f"known: {', '.join(PLATFORMS) or '(none)'}", file=sys.stderr)
            return 2

    return asyncio.run(bootstrap(plat, args.url, args.timeout))


if __name__ == "__main__":
    sys.exit(main())
