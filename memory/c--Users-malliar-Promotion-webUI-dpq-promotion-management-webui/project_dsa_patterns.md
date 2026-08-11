---
name: project_dsa_patterns
description: "DSA pattern-drilling tracker for Arun's FAANG SDE-2 prep — one pattern at a time, recognition-focused"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0af61243-6f0f-4a92-8060-9c367d361157
  modified: 2026-07-29T06:48:51.480Z
---

Teaching Arun the ~14 core DSA patterns for FAANG SDE-2 interviews (started 2026-07-08). Chosen over system design/portfolio/writing as the near-term focus to close his medium-difficulty gap. Supports [[project_faang_roadmap]] and complements [[project_system_design_learning]].

**Method:** recognition over volume. Per pattern: learn the template → 2 easy + 4 medium + 1-2 hard back-to-back → write the one-sentence "trigger" → spaced re-solve one problem a week later. Keep it small/fast per [[feedback_test_scenarios]] instinct — own a pattern, don't grind randomly.

**Pattern order & status:**
1. Two Pointers — DONE (2026-07-08). Covered Big-O foundation (Topic 0) first. Both flavors: converging (reverse, valid palindrome incl. alphanumeric/case, two-sum-sorted) + slow/fast (move zeroes, remove duplicates). Arun wrote remove-duplicates correctly from scratch. Note: he mixes Python syntax in (.append→.push); reassure often — he gets discouraged ("I'm so bad") but reasons out correct algorithms. From now on teach the optimal in-place O(1) approach, not the extra-array version.
2. Sliding Window — DONE (2026-07-08). Fixed window (max-sum-of-k, add-entering/subtract-leaving) + dynamic window (longest-substring-without-repeat, grow-then-shrink with Set). Arun wrote the dynamic version correctly from scratch — only typos (new set→Set, left left→let, Match→Math, return placed outside fn braces). Recurring: JS syntax slips + brace-placement; logic is consistently sound.
3. Fast & Slow Pointers — todo
4. Binary Search (+ on the answer) — todo
5. BFS/DFS (trees & graphs) — todo
6. Backtracking — todo
7. Monotonic Stack — todo
8. Heap / Top-K — todo
9. Intervals — todo
10. DP 1D — todo
11. DP 2D / grid — todo
12. DP subsequences (LCS/LIS) — todo
13. Union-Find (DSU) — todo
14. Trie — todo

**How to run a session:** resume at the first non-done pattern, teach the template, drill with him, capture his "trigger" sentence. Update status here as patterns complete.

**SWITCHED to Blind 75 walkthrough (2026-07-15):** Arun wants to work the Blind 75 list one problem at a time, in the grouped/topic order (Arrays&Hashing → Two Pointers → Sliding Window → Stack → Binary Search → Linked List → Trees → Tries → Heap → Backtracking → Graphs → DP → Intervals → Greedy → Math/Bits). Rhythm he likes: he attempts → I grade every bug line-by-line → lock the one-sentence takeaway. Started at Arrays&Hashing #1 Two Sum. His recurring gaps: off-by-one loop bounds (plug-in-a-tiny-number check), JS-vs-Python syntax slips (.append→.push), compound-operator typos (+=/-=), Map-is-not-a-number, ASI on `return` newline. Algorithmic thinking is consistently sound — reassure, he gets discouraged.
