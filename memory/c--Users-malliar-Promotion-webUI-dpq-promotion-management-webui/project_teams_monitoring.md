---
name: teams-monitoring-setup
description: "Arun's core team members and the Teams chats to monitor for tags/UI issues"
metadata: 
  node_type: memory
  type: project
  originSessionId: 46ffac7e-314a-4fba-9f31-2e20ce925325
  modified: 2026-07-23T14:12:43.470Z
---

Arun's core team: Vijaya (Vijaya.Yele), Roja (Roja.Rajappa), Vrashabh (Vrashabh.Argekar), Sudarshan (Sudarshan.BG), Ashutosh (Ashutosh.Nayak) — these people matter most.

Chats to monitor (set up 2026-07-23, via `read_resource` with `teams:///chats/{id}/messages` — chat_message_search rate-limits):
- **Internal DPROM** group chat: `19:b6420f2549224a8cb1a158e2557d57d9@thread.v2` (8 members, all core team)
- **PME-V I Stand Up** meeting chat (the 12:30 PM IST standup): `19:meeting_ZjkyYTI4ZDUtMzgzMC00ZWQ2LWJlMzAtZmM1ODIwMjk3ZmVl@thread.v2`

**Why:** Arun asked (2026-07-23) for notifications when these people/groups tag him or mention a UI issue, plus a debug attempt + drafted reply he can review and send. No Teams send tool is available — draft only, Arun sends manually.

Now runs as **cloud routine** `trig_01MA6Hq5X73Gf4XV7eE7rupF` (https://claude.ai/code/routines/trig_01MA6Hq5X73Gf4XV7eE7rupF): hourly, weekdays 9 AM–7 PM IST (cron `30 3-13 * * 1-5` UTC), notifies via email to Arun.Mallikarjun@tecnotree.com. Cloud can't reach git.tecnotree.com. Local session loop was stopped in favor of this.

**M365 connector is READ-ONLY everywhere (verified 2026-07-23):** outlook_send_mail / outlook_create_draft return "tool not available" locally, and in cloud runs the write tools never load (Mail.Send not granted; connector tool list is read/search only). **Notification solution: Teams Incoming Webhook** — Arun created a Workflows "Send webhook alerts to a channel" flow posting to his private "Arun Alerts" team channel; the routine POSTs an Adaptive Card (`{"type":"message","attachments":[{contentType: application/vnd.microsoft.card.adaptive, ...}]}`) via curl. Webhook URL is embedded in the routine prompt (secret — don't paste elsewhere). Gotcha: payload must be ASCII (em dashes/smart quotes → InvalidRequestContent from Windows curl); HTTP 202 = success. Second gotcha: the cloud environment ("My testing", env_0112bQFwfBJ3mALxbt61bA2j) egress-blocked the webhook host (403 on CONNECT to *.powerplatform.com) — environment network allowlist must include *.powerplatform.com for the routine's curl to work; MCP connector traffic is unaffected by egress policy.

Also: routine watches 6 chats now — the 2 groups + 1:1s with Vrashabh, Vijaya, Roja, Sudarshan (no Ashutosh 1:1 exists yet). 1:1 messages need a UI-issue keyword to match.

Code access for the cloud agent: 5 source bundles (`dpm-code-1..5*.txt`, `========== FILE: ==========` separators, all of dpm/src except shadcn ui/ + logos) were generated 2026-07-23; Arun must manually upload them to a OneDrive folder named **`dpm-code`** (Claude's own upload was blocked by the auto-mode permission classifier — bulk code copy/exfil pattern; expect the same block if retrying). Routine prompt already tells the agent to sharepoint_folder_search 'dpm-code' and read at most one bundle per run; if absent it falls back to context-only triage. Bundles are stale snapshots — regenerate + re-upload after significant UI changes.

**How to apply:** In monitoring loops, read the two chat message feeds, filter messages newer than last check, match "Arun"/@-mentions and UI-issue keywords (UI, issue, bug, screen, logout, not working, error). Notify via PushNotification, debug in this repo if the issue is UI-related, and draft a reply.
