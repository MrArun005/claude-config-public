"""apply/sources.py — the public job feeds, and how to find which one a company uses.

Most people search aggregators. The interesting property of an ATS feed is that
it is *upstream* of them: a posting exists on the company's own board the moment
recruiting publishes it, and reaches an aggregator whenever that aggregator next
crawls. Reading the ATS directly is how you see a job first.

Five ATS platforms publish an unauthenticated JSON feed of a company's open
roles. All five are documented, meant to be consumed, and are what the company's
own careers page calls to render itself:

    greenhouse       boards-api.greenhouse.io/v1/boards/<slug>/jobs
    ashby            api.ashbyhq.com/posting-api/job-board/<slug>
    lever            api.lever.co/v0/postings/<slug>?mode=json
    smartrecruiters  api.smartrecruiters.com/v1/companies/<slug>/postings
    workable         apply.workable.com/api/v1/widget/accounts/<slug>

The hard part is not reading a feed, it is knowing that a company has one and
under which slug. `discover()` answers that by probing a candidate slug against
every platform and keeping whatever answers with jobs.

    python -m apply.sources --discover gitlab,ramp,vercel     # probe a few
    python -m apply.sources --discover-file names.txt -o boards.yaml
    python -m apply.sources --show ashby:ramp                 # peek at a feed

Nothing here touches a site whose operator has asked agents away; check
robots.txt before adding a platform.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import paths

IST = timezone(timedelta(hours=5, minutes=30))
UA = "autoapply/1.0 (personal job search)"
TIMEOUT = 20


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _iso(value):
    """Parse the several timestamp shapes these APIs use. None if unusable."""
    if value is None:
        return None
    if isinstance(value, (int, float)):          # Lever: epoch milliseconds
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(
            timezone.utc)
    except ValueError:
        return None


# --- one normaliser per platform -------------------------------------------
# Each returns a list of dicts: title, location, url, published, remote.

def _greenhouse(slug: str):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    out = []
    for j in data.get("jobs", []):
        out.append({
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "published": _iso(j.get("first_published") or j.get("updated_at")),
            "remote": None,
        })
    return out


def _ashby(slug: str):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    out = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        out.append({
            "title": j.get("title", ""),
            "location": j.get("location", "") or "",
            "url": j.get("applyUrl") or j.get("jobUrl", ""),
            "published": _iso(j.get("publishedAt") or j.get("updatedAt")),
            "remote": j.get("isRemote"),
        })
    return out


def _lever(slug: str):
    data = _get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for j in data if isinstance(data, list) else []:
        cats = j.get("categories") or {}
        out.append({
            "title": j.get("text", ""),
            "location": cats.get("location", "") or "",
            "url": j.get("hostedUrl") or j.get("applyUrl", ""),
            "published": _iso(j.get("createdAt")),
            "remote": None,
        })
    return out


def _smartrecruiters(slug: str):
    data = _get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100")
    out = []
    for j in data.get("content", []):
        loc = j.get("location") or {}
        city = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x)
        out.append({
            "title": j.get("name", ""),
            "location": city,
            "url": (f"https://jobs.smartrecruiters.com/{slug}/"
                    f"{j.get('id', '')}"),
            "published": _iso(j.get("releasedDate")),
            "remote": loc.get("remote"),
        })
    return out


def _workable(slug: str):
    data = _get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
    out = []
    for j in data.get("jobs", []):
        out.append({
            "title": j.get("title", ""),
            "location": ", ".join(x for x in (j.get("city"), j.get("country")) if x),
            "url": j.get("url") or j.get("shortlink", ""),
            "published": _iso(j.get("published_on") or j.get("created_at")),
            "remote": j.get("telecommuting"),
        })
    return out


PLATFORMS = {
    "greenhouse": _greenhouse,
    "ashby": _ashby,
    "lever": _lever,
    "smartrecruiters": _smartrecruiters,
    "workable": _workable,
}


def fetch(platform: str, slug: str):
    """Normalised postings for one company on one platform."""
    fn = PLATFORMS.get(platform)
    if fn is None:
        raise ValueError(f"unknown platform {platform!r}; "
                         f"known: {', '.join(PLATFORMS)}")
    return fn(slug)


def probe(slug: str, platforms=None) -> list:
    """Which platforms serve this slug, and how many jobs each has.

    An empty feed is treated as a miss: plenty of slugs resolve on a platform
    the company does not actually use, and a board with no jobs is no use
    either way.
    """
    found = []
    for name in (platforms or PLATFORMS):
        try:
            jobs = fetch(name, slug)
        except (urllib.error.HTTPError, urllib.error.URLError,
                json.JSONDecodeError, TimeoutError, ValueError, OSError):
            continue
        except Exception:
            continue
        if jobs:
            dated = [j["published"] for j in jobs if j["published"]]
            found.append({
                "platform": name, "slug": slug, "jobs": len(jobs),
                "newest": max(dated) if dated else None,
            })
    return found


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m apply.sources",
        description="Find which ATS a company publishes on, and read the feed.")
    ap.add_argument("--discover", help="comma-separated company slugs to probe")
    ap.add_argument("--discover-file", help="file with one slug per line")
    ap.add_argument("--platforms", help="limit probing to these platforms")
    ap.add_argument("--show", metavar="PLATFORM:SLUG",
                    help="print the newest postings from one feed")
    ap.add_argument("-o", "--out", help="write discovered boards to this YAML file")
    args = ap.parse_args(argv)

    paths.init_console()

    if args.show:
        platform, _, slug = args.show.partition(":")
        jobs = fetch(platform, slug)
        jobs.sort(key=lambda j: j["published"] or datetime.min.replace(
            tzinfo=timezone.utc), reverse=True)
        print(f"\n{len(jobs)} postings from {platform}:{slug}\n")
        for j in jobs[:15]:
            when = (j["published"].astimezone(IST).strftime("%d %b %H:%M IST")
                    if j["published"] else "no date")
            print(f"  {when:>18}  {j['title'][:58]}")
            print(f"  {'':>18}  {j['location'][:58]}")
        return 0

    slugs = []
    if args.discover:
        slugs += [s.strip() for s in args.discover.split(",") if s.strip()]
    if args.discover_file:
        with open(args.discover_file, encoding="utf-8") as fh:
            slugs += [line.strip() for line in fh
                      if line.strip() and not line.startswith("#")]
    if not slugs:
        ap.error("give --discover, --discover-file, or --show")

    platforms = ([p.strip() for p in args.platforms.split(",")]
                 if args.platforms else None)
    hits, total_jobs = [], 0
    print(f"probing {len(slugs)} slug(s) across "
          f"{len(platforms or PLATFORMS)} platform(s)...\n")
    for slug in slugs:
        for hit in probe(slug, platforms):
            total_jobs += hit["jobs"]
            newest = (hit["newest"].astimezone(IST).strftime("%d %b")
                      if hit["newest"] else "?")
            print(f"  {hit['platform']:16} {hit['slug']:22} "
                  f"{hit['jobs']:5} jobs   newest {newest}")
            hits.append(hit)

    print(f"\n{len(hits)} board(s) found, {total_jobs} postings total")
    if args.out and hits:
        lines = ["# Discovered job boards. Feed this to apply.watch.", "boards:"]
        for h in sorted(hits, key=lambda h: -h["jobs"]):
            lines.append(f"  - platform: {h['platform']}")
            lines.append(f"    slug: {h['slug']}")
            lines.append(f"    jobs: {h['jobs']}")
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
