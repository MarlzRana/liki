---
name: setup-existing-wiki
description: Set up an EXISTING wiki's tooling on a new machine (qmd, git, PDF tooling, MCP server config). Use when the vault already exists and needs its toolchain installed on another computer. To create a brand-new wiki from scratch, use install-wiki instead.
disable-model-invocation: true
---

# Set Up an Existing Wiki on a New Machine

This assumes the vault **already exists** — synced via the owner's cloud storage (iCloud is the common choice), or clonable from their git repo. To create a new wiki from nothing, that's the `install-wiki` skill instead.

Run through the following setup steps. Check each one and skip if already done.

**Two kinds of machine:**
- **Personal machine** — the full vault, synced via the owner's cloud storage (all domains, private inbox/assets). Do the full setup below.
- **Work / shared machine (nothing personal on it)** — do NOT sync the private vault. Instead `git clone <your-wiki-git-remote>` (`<to_be_determined_from_install_skill>` — the git "fork" install-wiki created), which contains only the public allowlist the owner chose (`assets/public/`, `inbox/public/`, any public `wiki/` domains, config). Capture public, non-personal notes into `inbox/public/`, then commit + push; process them later on the personal machine (which pulls, files them into the wiki, and archives the originals to the private `inbox/processed/`). qmd/embeddings are optional here.

## 1. Git

```bash
cd "<vault-path>"
git init
```

If already a git repo, skip.

**Skills layout:** project skills live in `.agents/skills/`, and `.claude/skills` is a relative symlink (`../.agents/skills`) pointing at it. Both are committed, so a clone or iCloud sync restores them as they are. If the symlink didn't survive (e.g. `core.symlinks` is false, or a tool overwrote it), recreate it from the vault root:

```bash
rm -rf .claude/skills && ln -s ../.agents/skills .claude/skills
```

**This layout is what the `skills` CLI itself expects.** `.agents/skills` is that tool's own canonical store (`UNIVERSAL_SKILLS_DIR` in `src/constants.ts`), 19 agents map to it directly, and `src/installer.ts` has a dedicated code path — plus a regression test — for the case where an agent's skills dir is a symlink to it. The symlink is only needed because Claude Code reads `.claude/skills` and has no `.agents/` awareness.

**Install with `--agent universal`**, which resolves straight to `.agents/skills/` and never touches `.claude/` at all:

```bash
npx skills add https://github.com/anthropics/skills --skill pdf --agent universal -y
```

Hand-written and installed skills then sit side by side in that one directory. Avoid `--agent claude-code`: it aims at `.claude/skills/<name>` and, because a single target directory makes the tool choose copy mode anyway (`src/add.ts:797-800`), it only lands in the right place *because* the symlink redirects it. Remove the symlink and it silently diverges. `--copy` is likewise unnecessary.

**A vendored skill that you have edited must not be listed in `skills-lock.json`.** For project scope, `skills update` takes every lock entry and unconditionally reinstalls it — `rm -rf` on the skill directory, fresh copy from upstream, no diff, no prompt, exit 0. Local edits are lost silently, and renaming the directory is *not* protection (you get a pristine duplicate alongside). Deleting its lock entry is what makes a skill invisible to `update` and `experimental_install`. Every skill here is unlisted for that reason, `process-pdf` deliberately so.

Symlinks inside iCloud Drive are fragile regardless of any tool — a stray `.claude/skills 2` is iCloud conflict-renaming, not the CLI, which has no rename path anywhere in its source. After installing a skill, sanity-check with `readlink .claude/skills` and recreate it with the `ln -s` above if it has been displaced. Because `.agents/skills/**` is git-tracked, any iCloud conflict copy shows up immediately in `git status` — that's the safety net.

## 2. qmd (search engine)

Install globally:
```bash
npm install -g @tobilu/qmd
```

Add the wiki collection:
```bash
qmd collection add "<vault-path>/wiki" --name wiki
qmd context add qmd://wiki "Personal knowledge wiki — organized notes on career, technical topics, research, personal development, travel, family, and projects"
```

Generate initial embeddings:
```bash
qmd embed
```

## 3. Claude Code MCP Server

Add qmd to Claude Code settings (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "qmd": {
      "command": "qmd",
      "args": ["mcp"]
    }
  }
}
```

This uses stdio transport — Claude Code manages the subprocess lifecycle.

## 4. Obsidian Plugins

Remind the user to install:
- **Dataview** plugin (for frontmatter queries)
- **Web Clipper** browser extension (configure to save to `inbox/`)

## 5. Obsidian Settings

Remind the user to configure:
- **Files and links → Default location for new attachments** → "In the folder specified below" → `assets`
- **Files and links → New link format** → "Absolute path in vault" — so pasted images embed as `![[assets/name.png]]` (explicit vault-root path) rather than a bare filename, matching the asset convention. (Captures land in `assets/`, which is **private by default**; processing renames the cryptic default name to descriptive kebab-case and promotes only public-note imagery to `assets/public/`.)
- **Files and links → Use [[Wikilinks]]** → on
- Optionally bind a hotkey for "Download all remote images" (e.g., Ctrl+Shift+D)

## 6. Document tooling (PDFs and other inbox artifacts)

`inbox/` accepts any file type (see `<inbox_artifacts>` in AGENTS.md), and PDFs need real tooling:

```bash
brew install poppler pandoc tesseract ffmpeg uv
```

- **poppler is not optional.** Claude Code's `Read` tool shells out to `pdftoppm` to render PDF pages, so without it a PDF cannot be read at all — the failure is an error, not a fallback.
- **pandoc** converts office docs and ebooks to markdown; **ffmpeg** inspects audio (it cannot transcribe); **tesseract** is a last resort for printed scans and should never be used on handwriting — read those pages as images instead.
- Python libraries come from **uv** on demand (`uv run --with pymupdf …`), so nothing is installed into the system Python. `pymupdf` covers page rendering, cropping, text, and image extraction with no system dependencies.

## 7. Verify

Run `qmd status` to confirm the collection is indexed and embeddings exist.

Confirm the PDF path works end to end by reading any PDF (`Read` with a `pages` range) and rendering a crop:

```bash
uv run --quiet --with pymupdf python -c "import pymupdf; print(pymupdf.open('<some.pdf>').page_count)"
```
