---
name: User-facing docs — no colors, no developer jargon
description: When writing user-facing docs/guides, avoid UI colors and developer terminology
type: feedback
originSessionId: 35f9cf40-e67a-44dd-bfa3-96e21b3b3818
---
When writing documentation intended for end users (not developers), do NOT:

- Reference UI colors ("blue tick-box", "red error", "greyed out") — colors change with themes and users with accessibility needs may not perceive them.
- Use developer/implementation terminology — examples to avoid: "toast", "backend", "JSON", "boolean / string / float / integer / stringarray", "API", "payload", "console".
- Expose internal type names. If the UI shows a tag like "Currency" or "Count", use only that visible label — not the underlying primitive type.

**Why:** The user explicitly flagged this on the Simulator user guide — these docs go to non-technical users who understand functionality but not code. Color references and dev jargon make the docs feel internal rather than user-facing.

**How to apply:** Whenever creating or editing a `*.md` guide, tutorial, or README that targets end users (business analysts, QA without dev background, customers, trainers), strip color cues and dev terms. Describe what the user sees on screen by its label and shape ("tick-box", "number box marked Currency", "message at the top of the screen"), not by color or underlying data type. Reserve developer terminology for `dpm/`-internal code comments and developer docs.
