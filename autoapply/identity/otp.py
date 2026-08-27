"""
identity/otp.py — P0: delete the human from the OTP code path.

Polls a Gmail mailbox over IMAP for a verification code that arrived AFTER
since_ts (captured immediately before clicking "Send code"), so a stale code
from a previous attempt can never be returned.

Setup (one time):
  1. Google Account → Security → 2-Step Verification → App passwords
  2. Create an app password, put it in ~/.autoapply/secrets.env:
        GMAIL_USER=you@gmail.com
        GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
  3. chmod 600 ~/.autoapply/secrets.env

No OAuth, no Google Cloud project, no admin consent. Runs entirely local.
"""

from __future__ import annotations

import asyncio
import email
import email.utils
import imaplib
import os
import re
import time
from dataclasses import dataclass
from email.header import decode_header
from pathlib import Path

import paths

CODE = re.compile(r"\b(\d{5,7})\b")
SECRETS = paths.under("secrets.env")


def _load_secrets() -> tuple[str, str]:
    env: dict[str, str] = {}
    if SECRETS.exists():
        for line in SECRETS.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    user = env.get("GMAIL_USER") or os.environ.get("GMAIL_USER", "")
    pw = env.get("GMAIL_APP_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD", "")
    if not (user and pw):
        raise RuntimeError(f"GMAIL_USER / GMAIL_APP_PASSWORD not found in {SECRETS}")
    return user, pw


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return " ".join(out)


def _body_text(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8",
                                          errors="replace")
        # fall back to html stripped of tags
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode(part.get_content_charset() or "utf-8",
                                          errors="replace")
                    return re.sub(r"<[^>]+>", " ", html)
        return ""
    payload = msg.get_payload(decode=True)
    if payload:
        return payload.decode(msg.get_content_charset() or "utf-8",
                              errors="replace")
    return ""


@dataclass
class Mail:
    subject: str
    body_text: str
    sender: str
    ts: float


class GmailMailbox:
    """Thin, reconnect-per-poll IMAP reader. Deliberately stateless:
    a fresh connection every poll avoids Gmail's idle-connection drops
    and keeps the failure mode 'retry next poll' instead of 'hung socket'."""

    def __init__(self) -> None:
        self.user, self.password = _load_secrets()

    def _fetch_recent(self, sender_hint: str, since_ts: float) -> list[Mail]:
        box = imaplib.IMAP4_SSL("imap.gmail.com")
        try:
            box.login(self.user, self.password)
            box.select("INBOX", readonly=True)
            # IMAP SINCE is date-granular; we over-fetch today's mail from the
            # sender and enforce the second-granular cutoff ourselves.
            date = time.strftime("%d-%b-%Y", time.localtime(since_ts))
            typ, data = box.search(None, f'(FROM "{sender_hint}" SINCE {date})')
            if typ != "OK" or not data or not data[0]:
                return []
            mails: list[Mail] = []
            for uid in data[0].split()[-10:]:  # newest 10 is plenty
                typ, raw = box.fetch(uid, "(RFC822)")
                if typ != "OK":
                    continue
                msg = email.message_from_bytes(raw[0][1])
                dt = email.utils.parsedate_to_datetime(msg.get("Date"))
                ts = dt.timestamp() if dt else 0.0
                if ts <= since_ts:
                    continue  # stale — belongs to a previous attempt
                mails.append(Mail(
                    subject=_decode(msg.get("Subject")),
                    body_text=_body_text(msg),
                    sender=_decode(msg.get("From")),
                    ts=ts,
                ))
            return sorted(mails, key=lambda m: m.ts, reverse=True)
        finally:
            try:
                box.logout()
            except Exception:
                pass

    async def recent(self, sender_hint: str, since_ts: float) -> list[Mail]:
        return await asyncio.to_thread(self._fetch_recent, sender_hint, since_ts)


async def wait_for_otp(mailbox: GmailMailbox, sender_hint: str, since_ts: float,
                       timeout: int = 120, poll: int = 5) -> str:
    """Poll for a verification code that arrived AFTER since_ts."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for msg in await mailbox.recent(sender_hint, since_ts):
            if m := CODE.search(msg.subject + " " + msg.body_text):
                return m.group(1)
        await asyncio.sleep(poll)
    raise TimeoutError(f"no OTP from {sender_hint} within {timeout}s")


if __name__ == "__main__":
    # Smoke test: trigger a code on the target site FIRST, then run this.
    #   python -m identity.otp proxify
    import sys

    async def main() -> None:
        hint = sys.argv[1] if len(sys.argv) > 1 else "proxify"
        t0 = time.time() - 300  # accept codes from the last 5 min for the smoke test
        print(f"Polling {hint!r} …")
        code = await wait_for_otp(GmailMailbox(), hint, since_ts=t0, timeout=120)
        dt = time.time() - (t0 + 300)
        print(f"OTP: {code}  (retrieved in {dt:.1f}s)")

    asyncio.run(main())
