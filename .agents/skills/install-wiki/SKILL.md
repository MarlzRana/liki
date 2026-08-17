---
name: install-wiki
description: Create a brand-new liki wiki from scratch — set up the git storage, the vault location, the folder structure, the toolchain, and Obsidian. Use when someone wants to start their own LLM-maintained knowledge base from the liki template. To set up an EXISTING wiki on another machine, use setup-existing-wiki instead.
disable-model-invocation: true
---

# Install a New liki Wiki

You are bootstrapping a brand-new personal knowledge base from the **liki** template
(`MarlzRana/liki`) for the person invoking you. By the end they have: their own git
"fork" of the template, a vault in their chosen location, the folder structure and
privacy they picked, the full toolchain installed, and Obsidian configured.

This is an **interactive, one-time** setup. Ask questions with the AskUserQuestion tool
and **do not proceed on an irreversible step (creating a repo, writing to their
filesystem) without explicit confirmation.** Work through the steps in order; check each
and skip if already satisfied.

<assumptions>
- **macOS** is assumed (iCloud, Homebrew, and the Obsidian CLI). On Linux/Windows, the
  git and tooling steps still apply; adapt the storage-location and Obsidian steps and
  tell the user what you changed.
- The user has the **GitHub CLI** authed (`gh auth status`) and **git** installed. If
  `gh` isn't authed, stop and ask them to run `gh auth login` (suggest they type
  `! gh auth login` in the prompt so its output lands in this session).
</assumptions>

## 1. Create their git "fork" of the template

Ask **two** things:

1. **Public or private?** A public wiki is browsable by anyone; a private one is not.
   (They can still keep individual domains private within a public repo — that's the
   allowlist in step 4. This choice is about the repo's default visibility and whether
   anything committed is world-readable.)
2. **Repository name** (default: `liki`, or suggest `wiki`).

**GitHub has no native private fork** — a fork of a public repo is always public and
cannot be flipped. So instead of `gh repo fork`, duplicate the template into an
independent repo (this is GitHub's documented "duplicating a repository" method, and it
works identically for public and private):

```bash
# 1. Create the empty destination repo
gh repo create <user>/<name> --<public|private> \
  --description "My personal LLM-maintained knowledge base (liki)"

# 2. Bare-mirror the template and push it into the new repo
git clone --bare https://github.com/MarlzRana/liki.git /tmp/liki-mirror
git -C /tmp/liki-mirror push --mirror https://github.com/<user>/<name>.git
rm -rf /tmp/liki-mirror
```

Confirm the destination repo name and visibility back to the user before running this.
The result is a standalone repo — not a GitHub network fork — which is what lets it be
private. Step 3 wires an `upstream` remote so template improvements can still be pulled.

## 2. Choose where the vault lives on disk

The vault is a normal folder. Where it lives determines how it syncs across devices.
Detect the options and recommend:

- **iCloud + Obsidian mobile (best if they have an Apple device):** check for the
  Obsidian iCloud container:
  ```bash
  ls -d ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/ 2>/dev/null
  ```
  If it exists, offer to create the vault there (e.g.
  `…/iCloud~md~obsidian/Documents/<name>`). This is the path that syncs to the Obsidian
  iOS/iPadOS app automatically.
- **iCloud Drive without Obsidian mobile:** if the container above is absent but
  `~/Library/Mobile Documents/com~apple~CloudDocs/` exists, tell them: installing
  **Obsidian on an iPhone/iPad** (with iCloud sync on) creates the synced container so
  the vault reaches mobile. If they have **no** Apple mobile device, place the vault
  directly in the iCloud Drive folder (`…/com~apple~CloudDocs/<name>`) — it still syncs
  to their Macs, just not to a phone.
- **No iCloud / prefers elsewhere:** ask where they want it.

**Encourage iCloud with Advanced Data Protection (ADP) turned on** if they plan to keep
anything sensitive in the vault — most of it will be private and unencrypted-at-rest
otherwise. Point them to Settings → [their name] → iCloud → Advanced Data Protection.
Don't turn it on for them; just recommend it.

Confirm the exact absolute vault path before writing anything.

## 3. Clone the fork to that location

```bash
git clone https://github.com/<user>/<name>.git "<vault-path>"
cd "<vault-path>"
git remote add upstream https://github.com/MarlzRana/liki.git   # pull template updates later
```

Then make sure the skills symlink survived the clone (it should, as git mode 120000):

```bash
readlink .claude/skills   # expect ../.agents/skills
# if missing:  rm -rf .claude/skills && ln -s ../.agents/skills .claude/skills
```

Everything from here operates inside the vault.

## 4. Choose top-level domains and their privacy

Recommend the template author's set as a starting point and let them add/remove:

> **Career, Family, Investments, Personal, Projects, Technical, Travel, Other**
> (see `<routing_guidance>` in AGENTS.md for what each is for)

For **each** chosen domain, ask **public or private**. A sensible, safe default is
*everything private*; a common pattern is a public `Technical/` domain with all personal
domains private. Nothing becomes public unless they opt it in.

Then:

- `mkdir -p wiki/<Domain>` for each chosen domain.
- **Rewrite the `PUBLIC ALLOWLIST` block in `.gitignore`** (the block marked
  `<to_be_determined_from_install_skill>`). For each **public** domain, add:
  ```
  !wiki/<Domain>/
  !wiki/<Domain>/**
  ```
  Leave private domains out — they stay ignored. Delete the placeholder comment line.
  **Write these lines inside the PUBLIC ALLOWLIST block only — above the final
  `*.local.md` line, never below it.** gitignore is last-match-wins, and `*.local.md`
  must stay last so a sensitive `.local.md` note can never be re-included by an
  allowlist and committed.
- **Update `AGENTS.md`:**
  - In `<directory_structure>` and `<domain_categories>`, replace the recommended-default
    listing with the domains they actually chose, marking each public/private.
  - In `<privacy_and_git>`, replace the `<to_be_determined_from_install_skill>` bullet
    with the concrete list of which domains are public.

## 5. Fill in `<about_the_owner>` in AGENTS.md

This block drives the editorial voice, so fill it properly. Interview the user:

- **Role, expertise, and the fields they know deeply** — so terminology is pitched right.
- **Current interests / focus** (fine if mixed and shifting).
- **How they capture notes** — typing, speech-to-text dictation, or both. Whichever it
  is, record that capture artifacts (dictation homophones/dropped words; typing
  typos) are to be fixed silently, never flagged.

Replace the entire `<to_be_determined_from_install_skill>` placeholder inside
`<about_the_owner>` with a concrete block in the same style as the guidance there.

## 6. Install the toolchain

```bash
# Node 22 (qmd's native better-sqlite3 is built against it). Prefer Volta or nvm;
# package.json already pins node 22 via Volta if they use it.
node --version   # confirm 22.x on PATH for qmd

# Search engine
npm install -g @tobilu/qmd

# Document tooling for the inbox (PDFs, office docs, audio inspection)
brew install poppler pandoc tesseract ffmpeg uv
```

`poppler` is **not optional** — Claude Code's `Read` tool shells out to `pdftoppm` to
render PDF pages, so a PDF is unreadable without it. Python libraries come from `uv run
--with <pkg>` on demand, so nothing is installed into the system Python.

Index the vault with qmd:

```bash
qmd collection add "<vault-path>/wiki" --name wiki
qmd context add qmd://wiki "Personal knowledge wiki — organized notes across the owner's chosen domains"
qmd embed
```

The repo already ships a project-scoped `.mcp.json` wiring qmd as an MCP server, so
Claude Code picks it up from the vault directory automatically — no global settings edit
needed.

## 7. Create the private bookkeeping files

`index.md` and `log.md` are **private** (gitignored) because they reference every domain,
public and private. The template can't ship them, so create them now:

- **`index.md`** — a human-browsable table of contents with one `##` section per chosen
  domain (empty for now; `process-inbox` fills it as pages are created).
- **`log.md`** — an append-only chronological record. Seed it with the install entry:
  ```
  ## [YYYY-MM-DD] install | Created wiki from the liki template. Domains: <list, with public/private>. Storage: <path>. Repo: <url> (<public|private>).
  ```
  Use today's date.

## 8. Open the vault in Obsidian

Ask the user to open the vault folder in Obsidian ("Open folder as vault" →
`<vault-path>`). This registers the vault, which the Obsidian CLI in the next step needs.
Confirm it's open before continuing.

## 9. Install and enable the Obsidian plugins

The template ships `.obsidian/community-plugins.json` listing the required plugins, but
not their code, so install it. With the vault open, use the Obsidian CLI:

```bash
obsidian plugin:install id=dataview   && obsidian plugin:enable id=dataview
obsidian plugin:install id=embed-html && obsidian plugin:enable id=embed-html
```

- **dataview** — frontmatter/dashboard queries over the wiki.
- **embed-html** — renders the self-contained HTML diagrams the wiki uses (see
  `CLAUDE_DESKTOP.md`).

If the CLI can't reach the vault, fall back to instructing the user through
Settings → Community plugins → Browse.

Also confirm the shipped attachment settings took effect (they're in `.obsidian/app.json`):
new attachments save to `assets/`, and if they want pasted-image embeds to use explicit
vault-root paths, set **New link format → Absolute path in vault** and **Use
[[Wikilinks]] → on**.

## 10. Wire up Claude Desktop for diagrams

The vault includes **`CLAUDE_DESKTOP.md`** — instructions for the Claude **Desktop** chat
app (distinct from Claude Code) on how to author diagrams that match this wiki's
conventions: one self-contained HTML document per diagram, dark-mode-safe, drawn for the
`embed-html` plugin.

Encourage the user to add it to Claude Desktop under **Settings → General → Instructions
for Claude** — either paste the contents of `CLAUDE_DESKTOP.md` there, or reference it as
`@CLAUDE_DESKTOP.md`. Explain the payoff: **Claude Desktop can then produce diagrams they
can download and copy-paste straight into a wiki page** (as `![[assets/public/name.html]]`
via embed-html), without re-explaining the format each time.

## 11. Open the vault on their phone or iPad (recommended, if they chose iCloud)

If the user has an iPhone or iPad **and** chose iCloud as the vault's storage in step 2,
recommend they open the wiki in the **Obsidian mobile app** now:

1. Install **Obsidian** from the App Store.
2. On first launch, choose **"Open folder as vault"** and pick the vault from iCloud —
   it lives in the `iCloud~md~obsidian/Documents/<name>` container that the desktop app
   already syncs to, so it appears automatically once iCloud has synced.

The payoff is **capture-on-the-go**: dictating or jotting a rough note straight into
`inbox/` from their phone, which is the primary way the wiki gets fed — messy captures in,
clean pages out later on the desktop via `/process-inbox`.

This only works if **iCloud** (not a local-only folder) was chosen as the storage medium
in step 2. If they picked a local path, there's nothing to open on mobile — mention that
they can move the vault into iCloud later if they want phone sync.

## 12. Wrap up

Summarise what was created (repo + visibility, vault path, domains + privacy, tools
installed) and point them at the next step:

- Drop a note or file into `inbox/` and run **`/process-inbox`** to file it.
- Pull future template improvements with `git fetch upstream && git merge upstream/main`
  (safe — the template is scaffolding and skills, not their notes).
- `install-wiki` stays in the vault; it's harmless and can be re-run or used to help set
  up a friend.
