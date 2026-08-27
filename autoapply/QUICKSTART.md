# Quickstart — running autoapply on your own machine

## Where this runs, and why it has to

On **your machine**, not in a cloud session. Three things must sit in the same
place, and all three are local:

1. **The browser profile** holding your live login cookies (`~/.autoapply/chrome-profile`).
   Plan §3.1: never the real Chrome profile, never synced, never committed.
2. **Your résumé PDF**, for the file-upload fields.
3. **Unblocked network and your own IP.** Plan §7 makes the residential IP a
   *feature*: a datacenter IP is what the v1 stack was blocked on, and applying
   from one raises the register's High-severity "candidate account suspended" risk.

A cloud sandbox has none of the three — job boards are commonly blocked by
network policy there, and there is no profile and no résumé. That is why
everything machine-specific is checked by `preflight.py` rather than assumed.

## Setup (once)

```powershell
git clone https://github.com/MrArun005/claude-config-public
cd claude-config-public\autoapply

py -m pip install -r requirements.txt
```

Do **not** run `playwright install` — plan §2 uses your installed browser, so
there is no download.

Now put the two personal files in place. Neither is in git (both are
gitignored, deliberately — they hold personal data):

```
state\answers.yaml              your answer bank
state\templates\why.j2          your "why this company" prose
```

If you do not have them, start from the templates and seed interactively:

```powershell
copy state\answers.example.yaml state\answers.yaml
copy state\templates\why.j2.example state\templates\why.j2
py -m state.seed                 # walks the 59-question catalogue in one pass
```

### If you do not have Google Chrome

Edge works — it is Chromium-based, and `msedge` is a supported Playwright
channel (verified). No Chrome install needed:

```powershell
$env:AUTOAPPLY_BROWSER_CHANNEL = "msedge"          # PowerShell
```
```cmd
set AUTOAPPLY_BROWSER_CHANNEL=msedge
```

Or point at any Chromium-based binary directly:

```powershell
$env:AUTOAPPLY_CHROME_PATH = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
```

`preflight.py` looks in the standard install locations and tells you exactly
which variable to set.

## Is this machine ready?

```powershell
py preflight.py
```

Checks fifteen things and exits 1 with a list if any of them blocks a real run:
Python version, the three imports, **a genuinely launched browser** (it opens
one and discovers fields on a probe page), the state directory and its
permissions, a stale profile lock, answer-bank coverage and any remaining
placeholders, **whether your résumé file actually exists**, whether `why.j2`
actually renders, the alias table, catalogue reachability, ledger writability,
and the OTP secrets and their file mode.

The résumé path is the most common first-run failure. Fix whatever it lists,
re-run until it says READY.

## First real posting — three steps, safest first

```powershell
# 1. See the mapping. Fills NOTHING, sends NOTHING.
py -m apply.runner "<apply-url>" --company "Acme" --role "Senior Frontend" --plan

# 2. Fill it for real, but never click submit. Watch it happen.
py -m apply.runner "<apply-url>" --company "Acme" --role "Senior Frontend" --dry-run --headed

# 3. Only when both look right. This SUBMITS.
py -m apply.runner "<apply-url>" --company "Acme" --role "Senior Frontend"
```

Read the `--plan` output before anything else. It prints every field it found,
the answer-bank key it mapped to, and the exact value that control would
receive — so a wrong mapping is caught before an employer ever sees it. A
submitted application cannot be recalled.

Anything that parks:

```powershell
py -m state.review              # answer it; written back so it never parks again
py -m state.review --list
```

Session expired on a platform that needs a login:

```powershell
py -m identity.bootstrap proxify        # opens a visible window; log in by hand
py -m identity.bootstrap --list
```

## Scheduling it (not yet)

Unattended runs are the point (§0's AHA target), but three pieces are missing
and one of them is a High-severity risk:

- **No discovery.** `discover.py` / `enrich.py` from §8 do not exist, so nothing
  produces job URLs.
- **No batch driver.** `apply.runner` takes exactly one URL per invocation.
- **No rate discipline (§7).** No per-platform daily cap, no enforced serialism,
  no human-pace delays. Scheduling applications without these is the riskiest
  configuration in the register.

When those exist, schedule it **locally** (Windows Task Scheduler or cron), not
in a cloud session — for the IP reason above. Headless is already the default,
and the single-writer profile lock makes a scheduled run fail loudly rather than
corrupt the profile if you have a browser window open on it.

## Honest status

Tested: field discovery, label→answer mapping, the submit gate, checkpoint and
replay-on-resume, ledger deduplication, dropdown/number alternates, and
plan-mode isolation — all against real Chromium driving real forms, 38 checks
plus 19 in subprocesses.

**Not tested: a single real ATS form.** The fixtures are hand-written, not
Greenhouse's or Workday's. Expect the first real posting to surface something —
multi-step wizards (the runner handles one page), custom React comboboxes that
ignore `select_option`, or a login flow. `--plan` is the cheap way to find out,
because it reports without acting.
