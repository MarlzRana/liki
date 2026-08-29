---
name: lint-wiki
description: Health-check the wiki for structural issues, contradictions, missing links, and content gaps. Use when the user asks to lint/review the wiki, or on a scheduled basis.
---

# Lint Wiki

You are performing a health-check on the wiki knowledge base. Your goal is to identify issues and suggest improvements — but **do not make changes without explicit consent**.

**Important:** If you are less than 95% confident about any finding or recommendation, ask the user to clarify before proceeding. When in doubt, present your reasoning and let the user decide.

## Checks to Perform

### 0. Searching the vault — read this first

**Do not use bare `grep` for vault-wide sweeps.** In this environment `grep` is a shell function wrapping `ugrep --ignore-files`, which honours `.gitignore` — so it silently returns *no matches* across the private trees (`inbox/`, `assets/`, and every private `wiki/` domain). A sweep that should have found a stale reference reports a clean bill of health instead.

Use `rg --no-ignore` (add `--hidden` to include dotfiles), or `/usr/bin/grep` to bypass the wrapper:

```bash
rg --no-ignore -l "some-asset-name" .
```

### 1. Structural Health

```bash
/usr/bin/python3 .agents/skills/lint-wiki/scripts/link_graph.py
```

Reports unresolved links, broken embeds, orphans, dead ends, and isolated pages in one pass. Definitions are documented in the script's docstring — note that `index.md` is deliberately excluded as a link source, since it links to every page and would otherwise mask every orphan.

> **Do not use `obsidian orphans` / `deadends` / `unresolved` for this.** They are unreliable on this vault: an audit on 2026-08-10 found `obsidian orphans` reported 9 orphans of which **5 were false positives** (pages with demonstrable incoming links), while **missing 25 real ones**. If you want a second opinion, cross-check with `rg`, not with the Obsidian CLI.

Report findings grouped by severity:
- **Unresolved links / broken embeds** (broken references — something was deleted or renamed)
- **Isolated pages** (no incoming *and* no outgoing links — the actionable metric)
- **Orphans** (no page links to them — might be forgotten or need connecting)
- **Dead ends** (pages that don't link anywhere — might need cross-references)

Some dead ends are legitimately terminal. Don't manufacture a link just to clear the count — only propose cross-references that a reader would actually follow.

### 2. Content Consistency

Read key wiki pages and check for:
- **Contradictions** between pages (e.g., one page says X, another says not-X)
- **Stale claims** that newer pages or sources may have superseded
- **Outdated information** (dates, versions, facts that may have changed)

Use qmd to find related pages that might contradict each other:
```bash
qmd search "topic" -c wiki
```

### 3. Missing Pages and Gaps

Look for:
- **Concepts mentioned frequently** across pages but lacking their own dedicated page
- **Entities** (people, tools, projects) referenced in multiple places without a page
- **Topics** where the wiki has shallow coverage but the user clearly has interest

The unresolved-links section of `link_graph.py` (step 1) already lists what is referenced but doesn't exist. For concepts mentioned in *prose* without ever being linked — the more common gap — count mentions instead:

```bash
for t in "KV cache" "RLHF" "PagedAttention"; do
  printf '%-20s %s page(s)\n' "$t" "$(rg --no-ignore -lie "$t" wiki/ | wc -l)"
done
```

Watch for false positives from substring matches (`heap` matches "cheap"); use `-w` or an explicit `\b` pattern when the term is short. Cross-check the result against `<about_the_owner>` in AGENTS.md — a topic they're actively studying with no page is a stronger finding than a merely frequent term.

### 4. Cross-Reference Quality

Check whether pages that should link to each other actually do:
- Pages in the same domain covering related topics
- Pages that reference the same entities or concepts
- Source summaries that should link to concept pages and vice versa

### 5. Index and Log Health

- Is `index.md` up to date? Are all wiki pages listed?
- Are there pages in `wiki/` not reflected in the index?
- Is `log.md` consistent with recent file modifications?

### 6. Frontmatter Consistency

Check that wiki pages have consistent frontmatter:
- Do all pages have `date`, `domain`, `tags`?
- Are domains correct (matching folder location)?
- Are tags consistent (no duplicates like "ml" vs "ML" vs "machine-learning")?

### 7. Asset Hygiene (Privacy, Paths, Names)

Assets are private by default: `assets/` is gitignored, and only `assets/public/` is committed. Embeds use explicit vault-root-relative paths (`![[assets/public/…]]` for public, `![[assets/…]]` for private) and image files use descriptive kebab-case names (see `<assets>` and `<privacy_and_git>` in AGENTS.md). Check for:

- **Privacy leaks:** files in `assets/public/` embedded *only* by private notes (notes in a domain that isn't committed), or by *no* note at all — these should be demoted to the private `assets/` root.
- **Inverse:** files in the private `assets/` root that a *public* (committed) note embeds — these should be promoted to `assets/public/`.
- **Path/location mismatch:** an embed whose path disagrees with where the file actually lives (e.g. `![[assets/public/foo.png]]` but the file is in the `assets/` root) — the embed won't resolve.
- **Bare-filename embeds:** any `![[name.ext]]` without an `assets/` or `assets/public/` prefix — should be rewritten to an explicit path.
- **Cryptic names:** files still named `IMG_*`, `Pasted image *`, or otherwise non-descriptive — should be renamed to kebab-case describing the image.
- **Duplicate basenames** across `assets/` and `assets/public/` — should be disambiguated.

```bash
/usr/bin/python3 .agents/skills/lint-wiki/scripts/asset_audit.py
```

This checks every rule above in one pass, scanning both `wiki/` and `inbox/` for references. It walks the filesystem rather than using `git ls-files --others --exclude-standard`, because `assets/` is gitignored and `--exclude-standard` would filter out precisely the private files the audit exists to check.

**Renaming or moving a flagged file also requires rewriting its embed path in every referencing note — across both `wiki/` and `inbox/` (including `inbox/processed/` and `inbox/public/`)**, since the path is explicit (not filename-resolved). Sweep for the old token with `rg --no-ignore -l "old-name" .` (see step 0 — bare `grep` will miss the private trees), then re-run the audit to confirm zero broken embeds.

Two categories are printed as `(info)` rather than as defects, because they are usually deliberate: assets with no reference anywhere, and assets referenced only by an archived `inbox/processed/` note. **Check `log.md` before reporting these** — past lints have explicitly accepted some (superseded diagrams the owner chose to keep, and captures left unembedded on purpose because they contain a bystander's likeness or are text overlaid on an unrelated photo). Re-flagging those each lint is noise.

### 8. Card Health (Anki pipeline, optional)

**Only if the Anki flashcard pipeline was enabled** during `install-wiki` (its optional Anki step). The scripts ship with the template, so presence proves nothing — `install-wiki` writes a `.anki-enabled` marker at the vault root only when the user opts in; skip this check if `test -f .anki-enabled` fails. See `<anki_flashcards>` in AGENTS.md for the model. Check the `## Anki Cards` blocks and their sync state. The markdown-structure checks are stdlib; the Anki-cross checks need the pinned venv (run with Anki desktop closed, or they hit the collection lock):

```bash
/usr/bin/python3 .agents/skills/lint-wiki/scripts/card_audit.py
uv run --with anki==<anki-version> python .agents/skills/lint-wiki/scripts/card_audit.py --with-anki
```

- **Malformed / unminted / duplicate ids** — these block reconcile; flag them for fixing before the next sync.
- **Privacy** — a `## Anki Cards` section on a non-git-public or `.local.md` page must not exist; nor may a public card embed a private (non-`assets/public/`) asset (the reconciler would abort — the audit previews it).
- **Unsynced edits** — the card's markdown text differs from what's in Anki: it was edited but not reconciled. Run the reconciler to push it. (This is a deterministic text diff, *not* a semantic "the page drifted from the card" signal — that judgment belongs to the prose-level checks above and the card-quality reviewer.)
- **Hand-edited / orphaned** — an id matching no note (a hand-edit, or a not-yet-synced new card), or a `wiki::synced` note matching no card (a pending suspend).

Report, don't auto-fix — same as every other check.

## Output

Present findings as a clear report grouped by category. For each finding:
- What the issue is
- Where it is (specific pages)
- Suggested fix (if obvious)

**Do NOT auto-fix anything.** Present the report and ask the user which items they'd like you to address. Then fix only what they approve.

## Suggestions

At the end, suggest:
- New pages that could be created to fill gaps
- New sources to look for (articles, papers) that could strengthen weak areas
- Questions worth exploring that the wiki doesn't currently answer

## After Lint

If the user approves fixes:
1. Make the approved changes
2. Update `index.md` and `log.md`
3. Run `qmd update && qmd embed`
4. Review the diff (`git status` / `git diff`) and commit it using the `commit` skill for the message
5. If any **card text** changed (e.g. a stale-answer fix) and the Anki pipeline was enabled (`.anki-enabled` present), run the reconciler so the edit reaches Anki: `uv run --with anki==<anki-version> python .agents/skills/process-inbox/scripts/anki_reconcile.py --dry-run` (then apply with the desktop closed)
