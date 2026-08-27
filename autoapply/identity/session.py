"""
identity/session.py — session health + re-auth escalation.

Order of escalation (v2 plan §3.3):
  1. session_alive()  → proceed
  2. automated re-login (credentials + wait_for_otp)
  3. headed human bootstrap (last resort, ~monthly per platform)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .otp import GmailMailbox, wait_for_otp


@dataclass(frozen=True)
class Platform:
    name: str
    account_url: str      # a page that requires login
    login_selector: str   # element that ONLY exists when logged OUT
    otp_sender_hint: str  # e.g. "proxify"
    login_url: str = ""
    email_selector: str = "input[type=email]"
    send_code_selector: str = "text=Send code"
    code_selector: str = "input[name=code]"


# Registry — fill in as platforms are onboarded.
PLATFORMS: dict[str, Platform] = {
    "proxify": Platform(
        name="proxify",
        account_url="https://career.proxify.io/profile",   # verify
        login_selector="input[type=email]",                # verify
        otp_sender_hint="proxify",
        login_url="https://career.proxify.io/login",       # verify
    ),
}


async def session_alive(ctx, platform: Platform) -> bool:
    page = await ctx.new_page()
    try:
        await page.goto(platform.account_url, wait_until="domcontentloaded")
        return not await page.locator(platform.login_selector).count()
    finally:
        await page.close()


async def relogin(ctx, platform: Platform, user_email: str,
                  mailbox: GmailMailbox | None = None) -> bool:
    """Automated email-OTP login. Returns True on success.
    Raises TimeoutError if the code never arrives — caller escalates to headed."""
    mailbox = mailbox or GmailMailbox()
    page = await ctx.new_page()
    try:
        await page.goto(platform.login_url, wait_until="domcontentloaded")
        await page.fill(platform.email_selector, user_email)
        t0 = time.time()  # captured BEFORE requesting the code — staleness guard
        await page.click(platform.send_code_selector)
        code = await wait_for_otp(mailbox, platform.otp_sender_hint, since_ts=t0)
        await page.fill(platform.code_selector, code)
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle")
        return await session_alive(ctx, platform)
    finally:
        await page.close()


async def ensure_session(ctx, platform: Platform, user_email: str) -> None:
    if await session_alive(ctx, platform):
        return
    if await relogin(ctx, platform, user_email):
        return
    raise RuntimeError(
        f"{platform.name}: automated re-login failed — run headed bootstrap:\n"
        f"  python -m identity.bootstrap {platform.name}"
    )
