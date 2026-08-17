# liki

**A template for your own LLM-maintained personal wiki.**

You capture notes messily — dictated on your phone, clipped from the web, typed
half-finished — into an `inbox/`. An LLM (via [Claude Code](https://claude.com/claude-code))
processes them into clean, cross-linked, human-readable pages in a wiki you browse in
[Obsidian](https://obsidian.md). The wiki is the durable, compounding artifact; the LLM
does the summarising, cross-referencing, filing, and bookkeeping.

`liki` is the scaffolding — conventions, skills, and structure — plus a one-command
installer that stands up your own copy. It ships **no personal notes**; you fill it with
yours.

## Credit

This is a concrete implementation of the **"LLM Wiki"** pattern described by
**Andrej Karpathy** in [this gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
(April 2026): rather than re-deriving answers from raw documents on every query (standard
RAG), an LLM incrementally builds and maintains a persistent markdown wiki — flagging
contradictions, pre-building cross-references, and accumulating synthesis over time. The
three-layer design (raw sources → LLM-maintained wiki → an `AGENTS.md` schema governing
conventions), the three operations (ingest / query / lint), and the `index.md` + `log.md`
navigation files all come from there. Karpathy in turn credits Vannevar Bush's 1945
[Memex](https://en.wikipedia.org/wiki/Memex). All credit for the idea is his; this repo is
just one way to run it.

**Make it yours — don't fork-and-diverge by hand. Use the installer below**, which sets up
your own git repo, your storage, your domains, and your toolchain, and wires an `upstream`
remote so you can pull future improvements.

## Install

You need [Claude Code](https://claude.com/claude-code), the
[GitHub CLI](https://cli.github.com) (`gh auth login`), Homebrew, and — recommended —
Obsidian on your devices. macOS is assumed (iCloud, brew, the Obsidian CLI).

Install the bootstrap skill globally, then invoke it from anywhere:

```bash
npx skills add https://github.com/MarlzRana/liki --skill install-wiki --agent universal claude-code -g -y
```

This installs `install-wiki` to the agent-agnostic `~/.agents/skills/` **and** symlinks it
into `~/.claude/skills/`, so it's discoverable whether you drive it with Claude Code or
another agent. (If you use a different agent, add its name to the `--agent` list.)

```
claude
> /install-wiki
```

`/install-wiki` is interactive. It will:

1. **Create your git "fork"** — public or private (GitHub has no native private fork, so it
   duplicates the template into a standalone repo; works for both).
2. **Pick where the vault lives** — detects iCloud + Obsidian, or asks. Encourages iCloud
   with Advanced Data Protection if you'll store anything sensitive.
3. **Clone it** to that location and wire the `upstream` remote.
4. **Choose your top-level domains** and mark each public or private — this writes your
   `.gitignore` allowlist and personalises `AGENTS.md`.
5. **Install the toolchain** — qmd (search), poppler/pandoc/tesseract/ffmpeg/uv (inbox
   document processing), and index your vault.
6. **Create your private `index.md` / `log.md`**, open the vault in Obsidian, and install
   the `dataview` + `embed-html` plugins.
7. **Wire up Claude Desktop** for paste-ready diagrams (see `CLAUDE_DESKTOP.md`).

## How it works, once installed

- **Capture:** drop anything into `inbox/` — text, PDFs, photos of handwriting, voice
  memos, office docs. Any file type is fair game.
- **Ingest:** run `/process-inbox`. Claude reads the captures, cleans up dictation/typing
  artifacts silently, routes each to a domain, cross-links related pages, and archives the
  original.
- **Query:** run `/query-wiki` to search and synthesise across your notes.
- **Lint:** run `/lint-wiki` to health-check for orphans, contradictions, and stale
  content.

**Privacy is default-on.** Everything under `wiki/`, `inbox/`, and `assets/` is private
(git-ignored) unless you explicitly allowlist a domain as public during install. `index.md`
and `log.md` are always private. Files ending in `.local.md` are never committed, anywhere.

The conventions the LLM follows live in [`AGENTS.md`](./AGENTS.md); the skills live in
[`.agents/skills/`](./.agents/skills/). Read them — they're the whole system.

## Layout

```
AGENTS.md            ← the schema: conventions + workflows the LLM follows (canonical)
CLAUDE.md            → symlink to AGENTS.md (so Claude Code, which reads CLAUDE.md, finds it)
CLAUDE_DESKTOP.md    ← diagram-authoring instructions for the Claude Desktop app
.agents/skills/      ← the skills (install-wiki, process-inbox, process-pdf, query-wiki,
                       lint-wiki, process-instagram-source, setup-existing-wiki)
.claude/skills       → symlink to .agents/skills (so Claude Code discovers them)
wiki/                ← your clean, organized pages (created per your chosen domains)
inbox/               ← capture zone (private; inbox/public/ is a git-synced drop zone)
assets/              ← imagery + preserved sources (private; assets/public/ committed)
```
