---
name: process-inbox
description: Process unorganized notes from the inbox into the structured wiki. Use when the user wants to organize captured notes, or when there are unprocessed items in inbox/ that the user has indicated they want filed.
---

# Process Inbox

You are processing raw, unorganized notes from `inbox/` into the structured `wiki/` knowledge base.

## Workflow

### 1. Scan
Read all files in `inbox/` that are NOT in `inbox/processed/`. These are unprocessed items — this includes anything in `inbox/public/` (public, non-personal notes captured on another machine, e.g. a work laptop, and synced via git). Ignore the `inbox/public/.gitkeep` placeholder.

**Unprocessed items are not necessarily markdown.** `inbox/` accepts any file type — PDFs, photos, voice memos, spreadsheets, ebooks — and a non-markdown capture is normal, not an error. So enumerate with `ls -A inbox/ inbox/public/` rather than globbing for `*.md`, or you will silently skip exactly the items that need the most work. (`inbox/` is gitignored, so this session's `grep` wrapper cannot see into it at all — use `ls`/`find`, or `rg --no-ignore`.) See `<inbox_artifacts>` in AGENTS.md for per-type handling, and use the **`process-pdf`** skill for any PDF.

If there are no unprocessed items, tell the user and stop.

### 2. Read and Batch
Read all unprocessed items. Group related ones together (e.g., multiple notes from the same meeting, notes on the same topic from different days).

### 3. Quiz the User

Ask questions until you are **95% confident** about where and how to organize each item/batch:
- Which domain(s) does it belong to? (Career, Family, Personal, Projects, Technical, Travel, Other)
- Should it be a new page or integrated into an existing page?
- What subfolder/nesting makes sense?
- Any specific preferences?

**Only ask what's genuinely unclear.** If placement is obvious, propose it directly. Don't over-quiz.

### 4. Present Final Plan

Before making any changes, present a clear summary:
- For each inbox item: where it will go, whether it creates a new page or updates existing, what the page will be called
- Get explicit consent before proceeding

### 5. Execute

For each item:
- Create or update wiki pages in the appropriate location
- Nest subfolders within domains as appropriate
- Add `[[wiki-links]]` to connect related pages
- **Images and diagrams:** Images are **private by default** — save to `assets/` (gitignored) — but **prefer public when eligible: promote an image to `assets/public/` whenever the note it's embedded in is filed under `wiki/Technical/` (and only then)**. Don't leave Technical imagery sitting in private `assets/`. Give each a **descriptive kebab-case** name (open the image and look at what it shows; never keep `IMG_*` / `Pasted image *` names). Embed with an **explicit vault-root-relative path**: `![[assets/public/name.png]]` for public or `![[assets/name.png]]` for private — not a bare filename. Obsidian drops new pastes into `assets/` (private) with cryptic names, so rename (and promote to `assets/public/` if the note is Technical) during processing. **If the image is already referenced elsewhere, update every reference to the new name/path — across both `wiki/` and any other `inbox/` items (including `inbox/processed/` and `inbox/public/`)**, e.g. by grepping the vault for the old `[[…name…]]` token. See `<assets>` in AGENTS.md.
- Add light frontmatter: `date`, `domain`, `tags`
- Fix speech-to-text artifacts, spelling, and grammar errors silently
- Follow voice rules from AGENTS.md (messy → synthesize, structured → preserve, personal → preserve voice)
- Ensure the result is coherent with existing wiki content

**Non-markdown items:** Extract the content first, then route the result exactly as you would a note. **PDFs go through the `process-pdf` skill** — a scan of the owner's handwritten notes gets transcribed with its hand-drawn diagrams cropped out and embedded, while a born-digital document gets treated as a source. Other types follow the table in `<inbox_artifacts>`. Two things to get right: **archive the original to `inbox/processed/` but also preserve it in `assets/` and link it from the page when it's a lasting reference** (per `<artifact_retention>`), and **never summarise a file you could not actually open** — flag it and leave it in `inbox/` instead.

**Instagram sources:** If a note points at an `instagram.com/p/` post (usually with `@Agent transcribe this`), use the **`process-instagram-source`** skill to extract it — the content lives in the slides, not the caption, carousels lazy-load, and yt-dlp does not work for image posts. Come back here for routing and archiving once you have the text.

**Old vault references:** Inbox notes may reference files from the old vault (`../my-obsidian-vault/...`). The note will usually specify what to import and how. If the import strategy is ambiguous or missing, ask the user to clarify. When importing, copy referenced images into `assets/` (private by default), promote to `assets/public/` only if the note is Technical, give them descriptive kebab-case names, and update the embeds to explicit paths (`![[assets/…]]` / `![[assets/public/…]]`) — per the **Images and diagrams** rule above.

### 6. Update Index and Log

- Update `index.md` with new/modified pages
- Append entries to `log.md` with format: `## [YYYY-MM-DD] ingest | description`

### 7. Archive

Move processed inbox items to `inbox/processed/` (private) — binaries included, exactly like notes. Items that arrived via `inbox/public/` also archive to `inbox/processed/` — this clears the public drop zone and removes the raw capture from git on the next push (the processed wiki page is the durable record).

**Collision handling:** If a file with the same name already exists in `inbox/processed/`, do NOT overwrite. Ask the user what to do and suggest semantically meaningful alternative names based on the note's content (e.g., if both are called `meeting-notes.md`, suggest `meeting-notes-standup.md` or `meeting-notes-planning.md`). Never silently overwrite archived files.

### 8. Re-index

Run:
```bash
qmd update && qmd embed
```

This ensures new content is immediately searchable. Do not prompt the user — just run it.

### 9. Commit

Review the diff (`git status` / `git diff`) and commit it on the default branch, using the `commit` skill for the message. If the diff is empty — the work was entirely in gitignored/private domains — there's nothing to commit; say so and stop.
