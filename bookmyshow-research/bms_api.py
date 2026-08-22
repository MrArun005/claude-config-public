#!/usr/bin/env python3
"""
BookMyShow private-API client — Mysuru / "Toxic" research helper.

Endpoint shapes and the header set below were read verbatim from public source
(see README.md "Provenance"). They are NOT verified against live BookMyShow:
the container this was written in has no egress to bookmyshow.com. Run this
from a machine with normal Indian internet access and it will tell you whether
each endpoint still answers.

Usage:
  python3 bms_api.py regions                       # find the Mysuru RegionCode
  python3 bms_api.py venues MYS                    # cinemas in that region
  python3 bms_api.py movie ET00XXXXXX              # resolve an event code
  python3 bms_api.py showtimes-venue <VENUECODE> 20260826
  python3 bms_api.py toxic <REGIONCODE>            # full Toxic sweep for a city
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error

# Bump this to the current Play Store version of com.bt.bms if calls start 4xx-ing.
# update_play_store_version.sh in the upstream repo pulls it from
# https://api-playstore.rajkumaar.co.in/json?id=com.bt.bms
APP_VERSION = "9.7.0"
APP_VERSION_CODE = APP_VERSION.replace(".", "") + "0"

# Static token embedded in the Android app. Not a user credential; it is the
# same for every install. If it stops working it has been rotated app-side.
TOKEN = "67x1xa33b4x432a352bb"
BMS_ID_PREFIX = "1.58092784."


def bms_id() -> str:
    # NOTE: the prefix already ends in "." and upstream joins with another ".",
    # producing "1.58092784..<millis>". That double dot is reproduced verbatim
    # because that is the form known to be accepted. Do not "fix" it blindly.
    return f"{BMS_ID_PREFIX}.{int(time.time() * 1000)}"


def headers(bid: str, region_code: str | None = None) -> dict:
    h = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; Google Pixel 3a Build/QQ1D.200105.002)",
        "x-bms-id": bid,
        "x-platform": "AND",
        "x-platform-code": "ANDROID",
        "x-app-code": "MOBAND2",
        "x-device-cake": "Android-Google Pixel 3a",
        "x-screen-height": "2094",
        "x-screen-width": "1080",
        "x-screen-density": "2.625",
        "x-app-version": APP_VERSION,
        "x-app-version-code": APP_VERSION_CODE,
        "x-network": "Android | WIFI",
        "x-latitude": "0.0",
        "x-longitude": "0.0",
    }
    if region_code:
        h["x-region-code"] = region_code
        h["x-subregion-code"] = region_code
    return h


def get(url: str, region_code: str | None = None, with_headers: bool = True):
    bid = bms_id()
    req = urllib.request.Request(url, headers=headers(bid, region_code) if with_headers else {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code}] {url}", file=sys.stderr)
        print(e.read()[:600].decode("utf-8", "replace"), file=sys.stderr)
    except Exception as e:
        print(f"[ERR] {url}: {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------- endpoints

def regions():
    """All BMS cities + their RegionCode. This is how you find Mysuru's code."""
    return get("https://in.bookmyshow.com/api/explore/de/regions", with_headers=False)


def venues(region_code: str):
    """All movie venues (cinemas) in a region. eventType=MT means 'movies'."""
    return get(
        f"https://in.bookmyshow.com/pwa/api/de/venues?regionCode={region_code}&eventType=MT",
        with_headers=False,
    )


def movie_synopsis(event_code: str, region_code: str = "BANG"):
    """Resolve an ET00... event code to a movie name / metadata."""
    return get(
        f"https://in.bookmyshow.com/api/movies/v1/synopsis/init?eventcode={event_code}&channel=mobile",
        region_code=region_code,
    )


def venue_showcase(venue_code: str):
    return get(f"https://in.bookmyshow.com/api/movies/v1/cinema/showcase?vc={venue_code}")


def showtimes_by_venue(venue_code: str, date_code: str):
    """Every movie + showtime at one cinema on one date. date_code = YYYYMMDD."""
    bid = bms_id()
    url = (
        "https://in.bookmyshow.com/api/v2/mobile/showtimes/byvenue"
        f"?appCode=MOBAND2&appVersion={APP_VERSION_CODE}&venueCode={venue_code}"
        f"&bmsId={bid}&token={TOKEN}&dateCode={date_code}"
    )
    req = urllib.request.Request(url, headers=headers(bid))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print(f"[ERR] {url}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------- helpers

def find_region(needle: str):
    data = regions()
    if not data:
        return []
    hits = []
    bucket = data.get("BookMyShow", data)
    for key in ("TopCities", "OtherCities"):
        for c in bucket.get(key, []) or []:
            blob = json.dumps(c).lower()
            if needle.lower() in blob:
                hits.append(c)
    return hits


def toxic_sweep(region_code: str, date_code: str = "20260826", title: str = "toxic"):
    """Walk every cinema in a region on release day and report Toxic showtimes."""
    v = venues(region_code)
    if not v:
        print("Could not list venues — endpoint may have changed.", file=sys.stderr)
        return
    arr = v.get("BookMyShow", {}).get("arrVenue", [])
    print(f"{len(arr)} venues in {region_code}\n")
    for venue in arr:
        vc, vn = venue.get("VenueCode"), venue.get("VenueName")
        data = showtimes_by_venue(vc, date_code)
        if not data:
            continue
        details = data.get("ShowDetails") or []
        if not details:
            continue
        for event in details[0].get("Event", []) or []:
            if title.lower() not in (event.get("EventTitle") or "").lower():
                continue
            print(f"== {vn} ({vc}) — {event.get('EventTitle')}")
            for child in event.get("ChildEvents", []) or []:
                lang = child.get("EventLanguage", "?")
                dim = child.get("EventDimension", "?")
                print(f"   [{lang} {dim}] code={child.get('EventCode')}")
                for st in child.get("ShowTimes", []) or []:
                    times = st.get("ShowTime", "?")
                    cats = st.get("Categories", []) or []
                    price = ", ".join(
                        f"{c.get('PriceDesc','?')}:{c.get('CurPrice','?')}"
                        f"({c.get('SeatsAvail','?')} avail)" for c in cats
                    )
                    print(f"      {times}  {price}")
        time.sleep(0.4)  # be polite; BMS IP-bans aggressive callers


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == "regions":
        needle = a[0] if a else "mysu"
        hits = find_region(needle)
        print(json.dumps(hits, indent=2) if hits else f"No region matched {needle!r}")
    elif cmd == "venues":
        d = venues(a[0])
        for v in (d or {}).get("BookMyShow", {}).get("arrVenue", []):
            print(f"{v.get('VenueCode')}\t{v.get('VenueName')}")
    elif cmd == "movie":
        print(json.dumps(movie_synopsis(a[0]), indent=2)[:4000])
    elif cmd == "showtimes-venue":
        print(json.dumps(showtimes_by_venue(a[0], a[1]), indent=2)[:8000])
    elif cmd == "toxic":
        toxic_sweep(a[0], a[1] if len(a) > 1 else "20260826")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
