---
name: pokemon-tcg-challenge-state
description: "Pokemon TCG AI Battle Challenge ($240k Kaggle) — official deadlines, engine facts, agent contract, decision to enter"
metadata: 
  node_type: memory
  type: project
  originSessionId: fb7d1d5a-9011-4d98-8bb2-5547f9aaffe3
  modified: 2026-08-07T07:16:07.426Z
---

Decided 2026-08-07 to enter the Pokémon TCG AI Battle Challenge (Kaggle), chosen because it matches proven strengths from [[kaggriculture-competition-state]] (engine reverse-engineering, measurement-driven iteration, replay mining).

**Why:** $240k strategy pool with only ~317 teams entered (vs 6,484 in free simulation track); top 8 strategy teams get $30k each, finalists play for +$50k/+$30k. Best odds-to-skill-fit of all open 2026 competitions surveyed.

**Official deadlines (verified via authenticated Kaggle API 2026-08-07):**
- Simulation (`pokemon-tcg-ai-battle`): entry/merger **2026-08-09 23:59 UTC**, submission 2026-08-16 23:59 UTC. Knowledge-only, 6,484 teams.
- Strategy (`pokemon-tcg-ai-battle-challenge-strategy`): entry/merger 2026-09-06, submission 2026-09-13, $240,000, 317 teams, max team size 5.
- USER MUST JOIN BOTH IN BROWSER (no API for rule acceptance). As of 2026-08-07 `userHasEntered: False` on both.
- Press-sourced, unverified against official rules: simulation entry required for strategy eligibility; judging = model approach 70% / deck concept 20% / report 10%.

**Engine facts (verified from installed package):**
- Env `cabt` ships in `kaggle_environments` (installed 1.32.3 at C:\kv, latest 1.32.5). Core game logic is a **compiled binary** (`cg/cg.dll` + .so/.dylib) — NOT readable Python like kaggriculture; only the ctypes wrapper (`cg/sim.py` 54 lines, `cg/game.py` 75 lines, `cabt.py` 210 lines) is source-readable.
- Agent contract: `agent(obs) -> list[int]`. First call `obs["select"] is None` → return 60-card deck (list of card IDs); after that return `maxCount` indices into `obs["select"]["option"]` (engine presents only legal moves). Win/loss reward ±1, crash/invalid = instant loss (-1).
- Verified locally 2026-08-07: `make('cabt'); env.run(['random','random'])` completes (32 steps, rewards [-1,1]).
- Submission format (per wmh/ptcg-abc repo): .tar.gz with main.py, deck.csv, engine cg/ folder.

**Reference repos (participant-published):** wmh/ptcg-abc (3 complete ladder agents + decks + cabt_eval.py/cabt_ab.py eval tooling; warns local sims mispredicted ladder rankings — "the real ladder is the only reliable judge"; pins kaggle-environments==1.30.1 to match ladder), TomBombadyl/kaggle_pokemon (workspace). Check ladder's actual engine version before trusting local evals.

**How to apply:** replicate the kaggriculture workflow — paired evals in the official cabt env, mine top-team replays from the public leaderboard once entered, never trust local-only rankings. Official SDK/card data/sample notebooks are on the Kaggle competition page (needs entry). Backup target after Aug 16: ARC-AGI-3 Sept 30 milestone ($25k/$10k/$2.5k, arcprize.org).
