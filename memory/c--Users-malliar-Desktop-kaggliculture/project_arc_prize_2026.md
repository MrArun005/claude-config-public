---
name: project-arc-prize-2026
description: "ARC Prize 2026 Paper Track — verified rules, deadlines, SOTA, and open niches for both code tracks (researched 2026-08-07)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 66475ee7-2b87-4513-8d4f-8a2301878d33
  modified: 2026-08-07T06:24:36.719Z
---

User joined **ARC Prize 2026 – Paper Track** on Kaggle (2026-08-06). Goal: a paper scoring >4.5/5 on the rubric ($375K equal-split pool) or top-3 ($50K/$20K/$5K). All facts below verified against arcprize.org / arxiv / official GitHub on 2026-08-07 by two research subagents.

**Paper Track rules:** paper must be linked to an actual Kaggle code submission on ARC-AGI-2 or ARC-AGI-3 ("code need not achieve a high score"). Rubric: six 0–5 criteria averaged — Accuracy, Universality, Progress (toward 85%), Theory, Completeness, Novelty. Deadlines: entry Oct 26, code submission **Nov 2, 2026**, paper **Nov 8, 2026** (Kaggle page says Nov 9; treat Nov 8 as safe). Results Dec 4. All solutions must be open-sourced (CC0/MIT-0-comparable). Kaggle evaluation is offline — no frontier APIs.

**ARC-AGI-2 track (static grids):** Kaggle rerun = 240 hidden tasks, 12h on 4×L4 (96GB). Constrained SOTA: NVARC 24.03% private / 27.64% semi-private (TTT + synthetic data + TRM ensemble). Unconstrained frontier: GPT-5.6 Sol 92.5%, Opus 5 90.4% (semi-private). 2025 Paper Prize: 1st TRM (7M params, 8% AGI-2, $50K), 2nd SOAR (evolutionary synthesis), 3rd CompressARC (76K params, MDL, no pretraining). Saturated: vanilla TTT, prompting, hand DSLs. Open: tiny recursive models, offline refinement loops, MDL, small-model SOAR, 2D-native architectures, efficiency science. Dataset: github.com/arcprize/ARC-AGI-2 (1000 train / 120 public eval).

**ARC-AGI-3 track (interactive games):** 135 envs (25 public demo / 55 semi-private / 55 private), 64×64 grid, 16 colors, ≥6 levels each, no instructions. RHAE scoring: min(1.15, human_actions/AI_actions)² per level, level-N weight N, 5×-human action cutoff. Kaggle: RTX 6000-class GPU, offline, Competition Mode (API-only, level resets only, one scorecard). Kaggle SOTA ≈1–1.6% (Milestone 1, June 30: Tufa Labs "The Duck" — Qwen 3.6 27B driving a Python REPL, $25K; finding: hand-crafted tools hurt). Frontier: Opus 5 (High) 30.16% public demo. API-scaffold papers: Rodionov executable world models (15/25 solved, arxiv 2605.05138), OPINE-World (20/25, arxiv 2607.01531). Prior-work corpus is tiny (~6 items). Milestone 2: Sept 30, 2026. Tooling: `pip install arc-agi`, github.com/arcprize/ARC-AGI-3-Kaggle-Starter.

**Key structural insight:** paper prizes decouple from leaderboard rank (8% scored $50K in 2025). AGI-3's near-empty literature makes Novelty/Accuracy criteria easier for a solo entrant; the headline open problem is distilling frontier executable-world-model scaffolds into offline small models (1.6% vs 58–78% gap).

**Decisions (2026-08-07, user-approved):** anchor to **ARC-AGI-3**; approach = **offline executable world-model agent** (symbolic CEGIS-lite rule induction + A* planning on CPU, small open LLM proposes/symbols-verify as phase-2 fallback; ablation = theory contribution). Dev compute: **Kaggle free quota only** — everything but the LLM fallback must run on local CPU (public games run locally at 2K+ FPS via `pip install arc-agi`). Project repo: `c:\Users\malliar\Desktop\arc-agi-3\` (git, MIT-0). Approved design spec: `docs/superpowers/specs/2026-08-07-offline-world-modeler-design.md` in that repo. Related: [[feedback-no-guessing]].
