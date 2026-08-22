# BookMyShow API research — Mysuru / *Toxic* (26 Aug 2026)

## TL;DR

I could **not** open BookMyShow's website or read its network tab from this
session — outbound egress from the sandbox is allowlisted, and every
BookMyShow host (`in.bookmyshow.com`, `www.bookmyshow.com`, `api.bookmyshow.com`,
`in.bmscdn.com`) is refused at the proxy with a 403 on CONNECT. `WebFetch`
is blocked for the same domains independently.

So instead of a live capture I reconstructed the private API from public
source code, verbatim, and wrote two runnable tools so you can finish the
capture in seconds on a machine with normal internet:

| File | What it does |
|---|---|
| `bms_api.py` | Direct client for BMS's private mobile API — regions, venues, showtimes, prices, seat availability |
| `capture_network.py` | Drives a real Chromium through Mysuru → Toxic and dumps a HAR + every JSON response (the literal "network tab" ask) |

**Status of every claim below: endpoint shapes are verified against source
code I read line-by-line. None of it is verified against live BookMyShow —
I had no way to send a request.** Anything I could not establish is marked
`UNVERIFIED` rather than guessed.

---

## 1. There is no official public API

BookMyShow publishes no developer API and no API docs. Everything below is
the app's own private backend, which is what the website and Android app
call. Treat it as undocumented and unstable.

## 2. The endpoints

### 2.1 Cities → RegionCode

```
GET https://in.bookmyshow.com/api/explore/de/regions
GET https://in.bookmyshow.com/api/explore/v1/discover/regions
```

No auth headers needed. Response nests under `BookMyShow.TopCities` and
`BookMyShow.OtherCities`; each entry carries `RegionCode`, `RegionName`,
`Alias`.

**This is the call that answers "what is Mysuru's region code".**
Region codes confirmed present in source: `MUMBAI`, `NCR`, `BANG`, `HYD`,
`AHD`, `CHD`, `PUNE`, `CHEN`, `KOLK`, `KOCH`.
Mysuru is *not* in that hardcoded list — `UNVERIFIED`. The web slug is
`mysore`, and `MYS` is a plausible code, but I will not assert it. Run:

```bash
python3 bms_api.py regions mysu
```

### 2.2 Cinemas in a region

```
GET https://in.bookmyshow.com/pwa/api/de/venues?regionCode={CODE}&eventType=MT
```

`eventType=MT` = movies. No auth headers needed. Returns
`BookMyShow.arrVenue[]` with `VenueCode` + `VenueName`.

### 2.3 Showtimes at a cinema on a date  ← the useful one

```
GET https://in.bookmyshow.com/api/v2/mobile/showtimes/byvenue
      ?appCode=MOBAND2
      &appVersion={APP_VERSION_CODE}
      &venueCode={VENUE}
      &bmsId={BMS_ID}
      &token={TOKEN}
      &dateCode=YYYYMMDD
```

For Toxic's release day, `dateCode=20260826`.

Response: `ShowDetails[0].Event[]` → each has `EventTitle`, and
`ChildEvents[]` per language/format carrying `EventCode`, `EventLanguage`,
`EventDimension` (2D / 3D / IMAX), and showtime rows with per-category
price and seats-available.

**This requires the mobile headers** (§3).

### 2.4 Movie metadata from an event code

```
GET https://in.bookmyshow.com/api/movies/v1/synopsis/init?eventcode={ET00…}&channel=mobile
```
Returns `meta.event.eventName`. Needs mobile headers incl. `x-region-code`.

### 2.5 Cinema metadata

```
GET https://in.bookmyshow.com/api/movies/v1/cinema/showcase?vc={VENUE}
```
Returns `data.venueName`.

### 2.6 HTML fallback (no headers, embedded JSON)

Venue page: `https://in.bookmyshow.com/buytickets/{venue-slug}/cinema-{regioncode-lower}-{VenueCode}-MT/{YYYYMMDD}`
Movie page: `https://in.bookmyshow.com/buytickets/{movie-slug}-{city}/movie-{regioncode-lower}-{ET00…}-MT/`

Both embed the full payload in a script tag as
`var UAPI = JSON.parse("…")` — same `ShowDetails[0].Event[…].ChildEvents[]`
shape as §2.3. Useful when the mobile API rejects you.

## 3. Required headers for the mobile API

Sent by the Android app; `MOBAND2` is its app code.

```
User-Agent:          Dalvik/2.1.0 (Linux; U; Android 10; Google Pixel 3a Build/QQ1D.200105.002)
x-bms-id:            1.58092784.<epoch_millis>
x-platform:          AND
x-platform-code:     ANDROID
x-app-code:          MOBAND2
x-device-cake:       Android-Google Pixel 3a
x-screen-height:     2094
x-screen-width:      1080
x-screen-density:    2.625
x-app-version:       9.7.0
x-app-version-code:  9700
x-network:           Android | WIFI
x-latitude:          0.0
x-longitude:         0.0
x-region-code:       <REGION>     # only on some calls
x-subregion-code:    <REGION>
```

`token=67x1xa33b4x432a352bb` is a **static build-time constant in the app**,
identical for every install — not a user credential, nothing of yours leaks
by using it. If it 4xx-es, it was rotated app-side.

`x-app-version` must track the live Play Store version of `com.bt.bms` or
calls start failing. Upstream refreshes it from
`https://api-playstore.rajkumaar.co.in/json?id=com.bt.bms`.

## 4. Getting Toxic's event code

Event codes look like `ET00310790` and appear in the movie page URL:

```
https://in.bookmyshow.com/{city}/movies/{movie-slug}/ET00310790
```

Toxic's specific `ET00…` code is `UNVERIFIED` — I could not reach BMS and it
appears in no public source I could fetch. `capture_network.py` extracts it
automatically and writes it to `capture/event_code.txt`.

## 5. Rate limiting — read this

BookMyShow **IP-bans** servers that poll aggressively; the upstream Telegram
bot was killed exactly that way ("Live Bot has been disabled because
BookMyShow blocked IP of server from which bot was operating"). `bms_api.py`
sleeps 0.4 s between venue calls. Do not remove that, and do not run a tight
polling loop from a datacentre IP.

## 6. What's confirmed about the film

- **Toxic: A Fairy Tale for Grown-Ups** — releases **26 August 2026**, matching your date.
- Kannada-language period gangster film, dir. Geetu Mohandas; Yash in a dual
  role, with Kiara Advani, Nayanthara, Huma Qureshi, Tara Sutaria.
- Advance booking is already live: ~350K tickets sold on BookMyShow in the
  first 24 hours.
- The UAE release was delayed; India is unaffected.

Mysuru-specific screen counts, venues and pricing need a live call — that's
what `bms_api.py toxic <REGIONCODE> 20260826` prints.

## 7. Running it

```bash
# 1. Find Mysuru's region code
python3 bms_api.py regions mysu

# 2. List Mysuru cinemas
python3 bms_api.py venues <REGIONCODE>

# 3. Every Toxic show in Mysuru on release day, with prices + seats left
python3 bms_api.py toxic <REGIONCODE> 20260826
```

Or capture the network tab for real:

```bash
pip install playwright && playwright install chromium
python3 capture_network.py --city mysore --movie toxic
# -> capture/bms.har, capture/endpoints.txt, capture/responses/*.json
```

The HAR imports directly into Chrome DevTools → Network → import.

## 8. Provenance

Everything in §2–§3 was read verbatim from these public repos, not recalled:

- `abinpaul1/BookMyShow-ticket-notifier-telegram-bot` — `src/bms_helper.rs`,
  `src/utils.rs`, `README.md`, `update_play_store_version.sh`
  (§2.1–§2.5, the entire header set, the token, the rate-limit warning)
- `deCodeIt/book-my-show-notification` — `BookMyShow.py`
  (§2.1, §2.2, §2.6 venue URL pattern and the `var UAPI` extraction)
- `rbkio/bms-web-scraper`, `wilspi` gist (§2.6 movie URL pattern)

Film facts in §6 come from Variety, IMDb News, Gulf News, m9.news and
Filmibeat coverage, cross-checked across sources.

## 9. Legal note

This is an undocumented private API. Scraping it is against BookMyShow's
terms of service. Fine for personal, low-volume use; don't build a product
on it.
