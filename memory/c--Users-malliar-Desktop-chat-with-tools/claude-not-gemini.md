---
name: claude-not-gemini
description: "Arun wants Claude (not Gemini) used for any LLM \"lifting\" tasks in his projects"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d005f423-54e9-4d8d-b66b-7f846d0b6f5c
---

When building features that call an LLM in Arun's projects, use Claude via `@anthropic-ai/sdk` (e.g. `claude-haiku-4-5` for cheap mapping tasks), not Gemini — even though resume-tailor has a Gemini provider.

**Why:** he said explicitly "you do any lifting task dont use gemini" (2026-07-02, while designing applyfill's field-mapping fallback).
**How to apply:** default new LLM integrations to the Anthropic SDK / `ANTHROPIC_API_KEY`; resume-tailor's `lib/ai/index.ts` getProvider() already prefers Claude when both keys exist. Related: [[resume-tailor-applyfill]].
