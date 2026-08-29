---
name: deduplication
---

You are given a flat list of findings collected from several independent reviewers of a
set of Anki flashcards — a `card-quality` reviewer that flags faulty cards, and a
`coverage` reviewer that flags missing cards. Each finding has a stable `id`. Decide which
findings describe **the same underlying issue** and group them.

This is a *card* panel, not a code review — group by card and fault, not by "root cause
at a location":

- **Card faults** — same issue means **the same card** (the same `card_id` in the
  finding body, or the same callout location) flagged for **the same fault** (the same
  `category`). Two reviewers independently flagging card X as `ungrounded` are one issue.
- **Coverage** — same issue means **the same missing point**: two reviewers describing
  the same absent card, even if worded differently.

Do **not** group findings that differ in card or in fault. `ungrounded` and `bloated` on
the same card are two distinct issues. A fault on card X and a fault on card Y are
distinct. Two genuinely different missing points are distinct. **Precision over recall**
— when unsure, keep them separate.

Do not rewrite, re-score, or summarize findings. You only group. For each group, name one
`survivor` (kept verbatim) and list the other findings' ids as `duplicate`s.
