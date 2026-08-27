# autoapply

OwnCrawl v2. Applies to one job posting per invocation, walking a four-rung
ladder from cheap-and-deterministic to human-in-the-loop, and refuses to submit
anything you did not write.

## Layout

```
paths.py                 $AUTOAPPLY_HOME — one place that decides where state lives
identity/
  browser.py             persistent Chrome profile, single-writer lockfile   (P1)
  otp.py                 Gmail IMAP verification-code retrieval             (P0)
  session.py             session health + automated re-login escalation     (P1)
  bootstrap.py           headed human login, the last resort                (P1)
apply/
  adapter.py             the ladder's contract: UnknownField, dispatch, cache
  fields.py              live form discovery + stable field signatures
  aliases.py             field -> answer-bank key, from the YAML table
  templates.py           strict Jinja2 rendering for TEMPLATE answers
  adapters/generic_form.py   rung-1 deterministic adapter
  runner.py              the orchestrator — walks rungs 1-4                 (P3)
state/
  ledger.py              sqlite, job_url UNIQUE — never apply twice         (P2)
  checkpoint.py          per-field atomic checkpoints — never lose 80%      (P2)
  answers.py             answer bank + the submit gate                      (P2)
  review.py              drain the review queue back into the bank
  answers.example.yaml   copy to answers.yaml and fill in
  field-aliases.yaml     label/name -> answer key, first match wins
  templates/why.j2.example   "why this company" scaffold (tracked)
  templates/why.j2           your real version (gitignored)
p0_test.py               P0 exit criterion (needs your Gmail app password)
p3_test.py               P3 exit criterion (real Chromium, local fixtures)
```

## Setup

```bash
pip install -r requirements.txt && playwright install chromium
mkdir -p ~/.autoapply && chmod 700 ~/.autoapply

cp state/answers.example.yaml state/answers.yaml         # then fill it in
cp state/templates/why.j2.example state/templates/why.j2  # then write the prose

python -m state.seed            # walk the 59-question catalogue in one pass
python -m state.seed --coverage # what is still unanswered
```

For platforms that need a login (P0/P1):

1. Google Account → Security → App passwords → create one
2. Write `~/.autoapply/secrets.env` (`GMAIL_USER`, `GMAIL_APP_PASSWORD`), `chmod 600`
3. Trigger a login code on the platform, then `python -m identity.otp proxify`

## Use

```bash
python -m apply.runner <job-url> --company "Acme" --role "Senior Frontend"
python -m apply.runner <job-url> --dry-run     # fill and stop, never submit
python -m apply.runner <job-url> --headed      # watch it work

python -m state.review                # answer what parked, write it back
python -m state.review --list
python -m identity.bootstrap proxify  # headed login when re-auth fails
```

## The ladder (apply/adapter.py §4)

| Rung | Trigger | Behaviour |
|------|---------|-----------|
| 1 | an adapter's `matches()` wins | discover fields, map via `field-aliases.yaml`, fill |
| 2 | adapter raises `UnknownField` | a `Resolver` names the answer key; the result is cached by `(platform, field_signature)` so the next run is rung 1 again |
| 3 | no adapter matched | park for review |
| 4 | anything unexpected | park, flag for a headed handoff — never a blind retry |

Field signatures strip digits from names and ids, because ATS platforms generate
per-posting ids for custom questions. Keep the digits and a resolution cached on
Monday never hits on Tuesday. The mechanism is tested (signatures survive
regenerated ids); the exact attribute spelling is a representative pattern, not
one confirmed against a live posting — verify it on a real apply page.

## The submit gate is the safety boundary

The runner **auto-submits as soon as `state.answers.may_autosubmit()` clears**,
so that function is the only thing between this tool and a real employer. It
requires all four:

1. every filled field's provenance is `sourced` or `template`;
2. no field the form marks **required** was left unfilled;
3. no value is still a placeholder (`TODO`, `XX–YY`, empty);
4. every TEMPLATE answer actually rendered under `StrictUndefined`.

Fail any one and the application parks in `~/.autoapply/review-queue.jsonl`
with the reason, having filled and checkpointed but submitted nothing.

Two consequences worth knowing:

- A fresh `answers.yaml` copied from the example is **all placeholders**, so the
  first run parks on everything. That is intended. `python -m state.review`
  walks you through the gaps.
- Nothing is ever approximated. A `<select>` whose options do not actually
  contain your answer is unresolved, not "closest match" — answering "5-10
  years" when you said 5 is the class of small lie this design exists to avoid.
  Legal consent checkboxes are never inferred either; the bank must carry an
  explicit `consent_privacy` answer.

## Deliberately not built yet

Rung 2's and rung 3's LLM resolver. `apply/adapter.py` says the engine is
"chosen at P3 gate", so rather than guess an engine, `NullResolver` declines and
the field parks. `MappingResolver` accepts a human-supplied mapping and seeds
the same cache; an LLM resolver drops in behind the `Resolver` protocol in
`apply/runner.py` without touching anything else.

Submission-confirmation detection is also absent: there is no generic success
signal across ATSs that could be verified rather than guessed, so the runner
records the URL it landed on and you confirm.

## Tests

```bash
python p3_test.py    # 37 checks (+8 in a subprocess), real Chromium against local fixture forms
python p0_test.py    # OTP retrieval; needs your Gmail app password
```

`p3_test.py` redirects all state to a throwaway `$AUTOAPPLY_HOME`, so it cannot
touch the real ledger, checkpoints, profile or answer bank. It proves the
"nothing submitted" cases server-side by counting hits on the fixture's
thank-you page, rather than inspecting a freshly loaded (and therefore always
empty) form.

## Privacy

`state/answers.yaml` is gitignored and holds personal data — never commit it.
So are `state/templates/why.j2` (personal prose), `chrome-profile/` (live session
cookies) and `secrets.env`. The tracked `*.example` files carry no personal data.
