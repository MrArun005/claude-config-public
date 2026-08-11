---
name: doodle-kit-roadmap
description: "Roadmap to turn the Doodle Story Kit artifact into a YT animation \"video factory\" (creators studied, missing assets, Remotion tech, pipeline, build order)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2a0d71fd-b1bf-4c85-9b83-2ec06c1c3b0c
---

Project (started 2026-07-02): extend the **Doodle Story Kit** artifact (https://claude.ai/code/artifact/e2f9c85a-37b9-42f5-ad3a-3690357f50ee) into a full YouTube animation production stack. Artifact source lives in session scratchpad as `template.html` + `engine.js` + `data-*.json` + `build.js` (may need regenerating in a new session — the artifact HTML itself contains everything and can be fetched via WebFetch).

**Style target**: between After Skool (whiteboard explainer) and Ice Cream Sandwich (wobbly ink + line boil). Most reachable first archetype = whiteboard explainer (no lip sync/character acting; draw-on synced to VO — engine already does this). Creators to study: TheOdd1sOut, Jaiden Animations, Domics, sWooZie, Ice Cream Sandwich (storytime); After Skool, RSA Animate, minutephysics, Sprouts, Improvement Pill (explainer); Casually Explained, Sam O'Nella, Pencilmation, Alan Becker (minimalist comedy). Key lesson: simple art is fine — writing, VO quality, and beat timing (one drawing/gag per 3–8s narration beat) do the work.

**Assets still missing from the kit**: hand-lettered alphabet + numerals; character system (2–3 recurring characters × ~8 poses × ~8 swappable expressions); 4-shape mouth set (closed/open/wide/oo); drawing-hand sprite; charts (growing bar, filling pie, drawing line-graph, counting number); composable scene backgrounds (room, street, desk, landscape — not 200×200 cards); YT furniture (subscribe/bell/like, end-screen frames, device mockups).

**Remotion tech still missing**: line boil (cycle 3 seed variants at 8–12fps — biggest "pro look" upgrade; engine's seeded reroll makes this trivial); erase/exit anims; `<DoodleScene>` composer (1920×1080 stage, per-asset entry times); virtual camera pan/zoom over one big canvas (After Skool signature); hand-follower via getPointAtLength; drawAt/popAt/boilAt + beat-based scheduling. Pipeline: script → beats JSON → Remotion timeline; Whisper word-level timestamps drive scene timing; render presets 16:9 1080p + 9:16 Shorts + thumbnail export; captions. Audio: VO first, pencil-scribble SFX synced to draw-ons, pops/whooshes, ducked music bed.

**Agreed build order**: (1) lettering + charts + YT furniture as engine presets in the artifact → (2) Remotion repo scaffold with DoodleScene/camera/timing helpers → (3) line boil + drawing hand → (4) Whisper→beats→timeline generator → (5) first explainer video (characters/mouths later). User was deciding between starting #1 (extend artifact) vs #2 (Remotion scaffold).
