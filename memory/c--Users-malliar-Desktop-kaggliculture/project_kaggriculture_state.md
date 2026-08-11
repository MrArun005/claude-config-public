---
name: kaggriculture-competition-state
description: "Kaggle kaggriculture competition — verified engine mechanics, top-clone meta facts, and version history v1-v4"
metadata: 
  node_type: memory
  type: project
  originSessionId: ec1a8cb4-0d22-42d5-b82d-b6649fbd40f6
  modified: 2026-08-05T15:42:35.066Z
---

Kaggle "kaggriculture" farming sim competition ($50k). Agent code in `repo/kaggriculture/` (main.py, rules.py, env_adapter.py). Venv at `C:\kv` (short path — project .venv breaks on Windows 260-char limit).

**Why:** User's goal is climbing the live leaderboard; new submissions always start ~600 and must EARN rating via win rate — there is no way to start at 2,000+.

**Verified engine facts (from `C:\kv\Lib\site-packages\kaggle_environments\envs\kaggriculture\kaggriculture.py`):**
- CARE: every fed+cared day banks +1 product, paid on next FED production day (:796-800). Cow interval 2, sheep 3. Perfect ritual = 3 milk/2d, 4 wool/3d.
- Animal unfed 2 consecutive days → escapes (:787-789). FEED consumes 1 WHEAT from unit's hand.
- FERTILIZE: 1 fert → fertilized_until_day=day+2; doubles ongoing-crop production on watered days (:769-770); WATER op adds nothing to ongoing crops (:381).
- Terminal: reward latched at step 718; step-719 auto-drop worthless.
- Starting cash 3000; pens free to build; land $1k/$2k/$4k.

**Top-clone meta (measured EXECUTED flows from replays 90153480/90154808 — never trust attempted-op counts):** all top players run one identical public agent: 21 melon seeds, 44 strawberry (27 tiles by day 12, 40 by 20), 8 cows + 6 sheep (4 animals by day 3, 14 by day 12, spend to $10), 100% daily feed+care (mathematical max production: 216 milk, 168 wool), ~107 FERTILIZE ops on strawberries, ~292 fert produced, 3 quadrants by day 12, endgame wheat refill (32 tiles day 28). Final scores 121k-141k. lucaskna additionally runs a wheat buy/sell market loop (27k-31k units).

**Version history (live ratings):** v1 720→632 (melon mono), v2 ~589 stagnant, v3 (sub 55269770) oscillates 593-695. v4 (built 2026-08-05, commit 3d1990a, **UNSUBMITTED** — user's bar: top-clone parity/160k, submit only on their go): concurrent animal ritual (care 40→85, feed 90 MUST outrank care), carried-animal census fix, feed-wheat accounting counts hands, strawberry 44 tiles ramp day 6-17 + FERTILIZE, melon 13 (tuner +5,973), land threshold 18 (3rd quad day 12), herd front-load (reserve 900, cow-led round-robin, 3/turn). Validation: beats v3-config 16/16 (124,588 vs 88,559), uncontested 140,757±5,229 (clone best 140,912), tuned contested self-play mean 114,698 (tuner converged, pass 2 no change). Repo has HANDOFF.md + handoff/ for machine migration; dashboard artifact ec31b8c7-03d9-4373-87dd-8fa67a92e00f.

**How to apply:** measure changes with `measure_flows.py` (executed shed/inv deltas) and `audit_animals.py` (daily fed/cared coverage) on a `gen_local_replay.py` episode; validate with paired-seed harness evals (`v4_eval.py` pattern) before any submission; run `test_agent.py` (21 checks) before submitting. Mirror-run totals vary by random seed — only paired seeds are comparable.
