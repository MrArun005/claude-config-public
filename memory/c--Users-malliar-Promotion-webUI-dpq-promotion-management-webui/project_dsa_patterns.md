---
name: project_dsa_patterns
description: "DSA pattern-drilling tracker for Arun's FAANG SDE-2 prep — one pattern at a time, recognition-focused"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0af61243-6f0f-4a92-8060-9c367d361157
  modified: 2026-08-12T13:05:21.495Z
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

**Detour 2026-08-12:** Arun brought GFG "K Sized Subarray Maximum" (= Sliding Window Maximum) and said deques confuse him. Taught it by deriving the structure instead of naming it: brute force → why "remember the max index" breaks when the max leaves the window → the kill rule ("a later element >= an earlier one makes the earlier one permanently useless") → what survives is a decreasing line of succession → deque is just "a list open at both ends", nothing more. Framed front=king / behind=ranked heirs. Emphasized: store INDICES not values, and the amortized O(n) argument (each index pushed once, popped once). Left him minimum-of-each-window as the from-scratch exercise. Blind 75 resume point unchanged: Arrays&Hashing #1 Two Sum.

**JS map/filter drill 2026-08-12 (same session):** He asked for interview-style map/filter problems. My first attempt (polyfills + `parseInt` gotchas + sparse arrays) got "i dint understand anything" — TOO FAST. Restarting from `for`-loop equivalence worked immediately: map = "always push something changed", filter = "push only if condition passes". Landed: map-vs-filter, filter-before-map ordering (map destroys the fields filter needs), chaining, template-string trio (backtick+$+braces), braces-in-arrow-body needs `return`. **Two diagnosed habits worth reusing:** (1) he PATCHES his previous wrong answer instead of rewriting from a blank line — fixed only the character I flagged and left the real bug in, 3x on the same problem; tell him "blank line, don't copy and adjust". (2) The "map or filter?" judgment call doesn't stick, but the mechanical **count check does** — input length vs expected output length; if they differ, map is ruled out by arithmetic. Prefer mechanical tests over intuition rules with him. Session ended on "brain fatigue" — he stops hard when tired, so wrap cleanly with ONE takeaway, not a summary wall.

**RESUME HERE (JS arrays):** `employees` dataset = [Arun/Engineering/90000/active, Roja/Design/75000/inactive, Vijay/Engineering/120000/active, Sudha/Sales/60000/active, Ashu/Design/85000/active]. He owes redos on: (1) names of inactive → `['Roja']`, (2) total Design salary → `160000`, (4) `'X works in Y'` strings for all 5, (6) lowest-paid name → `'Sudha'`, (7) name→salary object → `{Arun:90000,...}`. Got #3 (`filter().length` → 2) and #5 (`map().sort()`) right cold.

**Two live bugs to re-drill:** (a) `=` vs `===` inside callbacks — he wrote `e.active = false` and `e.dept = "Design"`, which mutate the real objects AND return the assigned value, so filter kept nothing / kept everything (430000 + every dept overwritten). Best teaching frame: same bug, opposite outcomes, decided by the assigned value's truthiness. (b) `return` written in a brace-less arrow → SyntaxError; he has the braces↔return rule backwards in one direction.

**SESSION FORMAT (agreed 2026-08-12):** He fatigues at ~30 min and flagged it, unsure whether that was a problem — it isn't, and I told him so (active production is expensive; Pomodoro is 25 min). Run sessions as **30 min / one topic / ~5 problems / then stop**. Biggest contributor to his drain was MY message length — he spent effort reading walls of explanation before he had any left for solving. Keep explanations short; the problems are where his budget should go. Reframe that worked: "the fatigue is the receipt" — when I solved everything for him he didn't get tired, because he wasn't working.

**What reliably works with him:** mechanical rituals, not intuition. The winner is the three-fact check before coding — "count in → count out, output type" (e.g. `5 → 1, object`). Every problem he got right, he'd run it; every one he missed, he'd skipped it. Also: he calls out being over-taught ("if you solve everything why me learning bro") — demo ONE, hand him the rest, hints not answers.

Also covered and landed: chaining, filter-before-map ordering, reduce accumulator + mandatory initial value, template strings, `sort` mutates the original (but sorting a map/filter result is safe), default `sort` is alphabetical so comparators are for numbers only. Not yet done: `myMap`/`myFilter`/`myReduce` polyfills (he skipped the Level 3 build), `Array.prototype`/`this`.
