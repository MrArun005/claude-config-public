#!/usr/bin/env python3
"""
Automated "open DevTools -> Network tab" capture for BookMyShow.

This is what I could NOT run here (no egress to bookmyshow.com from the
sandbox). Run it on your own machine and it will drive a real Chromium
through the Mysuru -> Toxic booking flow, record every XHR/fetch, and dump:

  - bms.har              full HAR, importable straight into Chrome DevTools
  - endpoints.txt        deduped list of API URLs actually called
  - responses/*.json     each JSON response body, one file per call

Setup:
    pip install playwright
    playwright install chromium

Run:
    python3 capture_network.py --city mysore --movie toxic
"""

import argparse
import json
import os
import pathlib
import re
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("pip install playwright && playwright install chromium")

OUT = pathlib.Path(__file__).parent / "capture"
API_HINT = re.compile(r"/api/|/pwa/api/|/serv/|showtimes|synopsis|venues|regions|quickbook", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="mysore", help="BMS city slug, e.g. mysore")
    ap.add_argument("--movie", default="toxic", help="substring of the movie title")
    ap.add_argument("--headless", action="store_true",
                    help="run without a visible window (BMS bot-checks are easier to pass headed)")
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    (OUT / "responses").mkdir(exist_ok=True)
    seen, idx = set(), {"n": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        ctx = browser.new_context(
            record_har_path=str(OUT / "bms.har"),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            geolocation={"latitude": 12.2958, "longitude": 76.6394},  # Mysuru
            permissions=["geolocation"],
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.new_page()

        def on_response(resp):
            url = resp.url
            if "bookmyshow" not in url or not API_HINT.search(url):
                return
            if resp.request.resource_type not in ("xhr", "fetch", "document"):
                return
            seen.add(f"{resp.request.method} {url}")
            ct = (resp.headers.get("content-type") or "")
            if "json" not in ct:
                return
            try:
                body = resp.json()
            except Exception:
                return
            idx["n"] += 1
            name = re.sub(r"[^a-zA-Z0-9]+", "_", url.split("?")[0])[-70:]
            path = OUT / "responses" / f"{idx['n']:03d}_{name}.json"
            path.write_text(json.dumps(body, indent=2)[:2_000_000])
            print(f"  captured {resp.request.method} {url[:110]}")

        page.on("response", on_response)

        print(f"[1] city page: {args.city}")
        page.goto(f"https://in.bookmyshow.com/explore/movies-{args.city}",
                  wait_until="networkidle", timeout=90_000)
        page.wait_for_timeout(3000)

        print(f"[2] looking for a '{args.movie}' link")
        link = page.locator(f"a[href*='/movies/']:has-text('{args.movie}')").first
        try:
            href = link.get_attribute("href", timeout=15_000)
            print(f"    -> {href}")
            code = re.search(r"(ET\d{8})", href or "")
            if code:
                print(f"    EVENT CODE: {code.group(1)}")
                (OUT / "event_code.txt").write_text(code.group(1))
            link.click()
            page.wait_for_load_state("networkidle", timeout=90_000)
            page.wait_for_timeout(3000)

            print("[3] opening showtimes (Book tickets)")
            for sel in ("text=Book tickets", "text=Book Tickets", "text=Buy Tickets"):
                btn = page.locator(sel).first
                if btn.count():
                    btn.click()
                    page.wait_for_load_state("networkidle", timeout=90_000)
                    page.wait_for_timeout(4000)
                    break
        except Exception as e:
            print(f"    could not auto-navigate ({e}).")
            if not args.headless:
                input("    Drive the browser to the showtimes page yourself, then press Enter...")

        ctx.close()
        browser.close()

    (OUT / "endpoints.txt").write_text("\n".join(sorted(seen)))
    print(f"\nHAR:       {OUT/'bms.har'}")
    print(f"Endpoints: {OUT/'endpoints.txt'} ({len(seen)} unique)")
    print(f"Bodies:    {OUT/'responses'} ({idx['n']} files)")
    for s in sorted(seen):
        print("  " + s[:160])


if __name__ == "__main__":
    main()
