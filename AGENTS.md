**Wiki Knowledge Base — Schema**

<what_this_is>
This is an LLM-maintained personal knowledge base. The owner captures notes messily in `inbox/` (via phone, desktop, web clipper, or speech-to-text), and Claude processes them into clean, organized wiki pages in `wiki/`.

**The primary audience for wiki content is the human browsing in Obsidian, not Claude.** Every page should be readable, useful, and navigable without Claude present.
</what_this_is>

<about_the_owner>
<to_be_determined_from_install_skill>
The `install-wiki` skill interviews the owner and writes this block. It should capture who they are and how they work, because the editorial rules below depend on it:
- **Role / expertise / domains** — so terminology can be pitched correctly (e.g. "Use correct terminology. Be simple but don't oversimplify" makes sense only once you know the owner's depth in a field).
- **Current interests / focus** — mixed and exploratory is fine; this shifts over time.
- **How they capture notes** — typing, and/or **speech-to-text dictation**. Dictation produces transcription artifacts (homophones, dropped words, garbled phrases, run-on sentences, missing punctuation); typing produces occasional spelling/grammar errors. Whichever they use, **both are normal and expected — fix them silently during processing, never flag them.**

Until this block is filled, treat the owner as a general-interest note-taker: correct terminology where you can, keep explanations clear, and fix capture artifacts silently.
</to_be_determined_from_install_skill>
</about_the_owner>

<directory_structure>
The top-level `wiki/` domains are chosen by the owner during `install-wiki`; the set below is the **recommended default** — `<to_be_determined_from_install_skill>` picks the actual folders and which of them are public vs private.
```
wiki/                       ← vault root
├── assets/                 ← imagery + preserved source files, PRIVATE by default (gitignored)
│   └── public/             ← assets for public notes only; committed
├── inbox/                  ← messy capture zone, ANY file type (owner writes here); PRIVATE by default (gitignored)
│   ├── public/             ← intentionally-public notes; committed (work→personal drop zone)
│   └── processed/          ← archived after integration; private
├── wiki/                   ← clean, organized, human-readable notes
│   ├── Career/             ← recommended default domains; the owner's chosen set
│   ├── Family/               is configured by install-wiki, and each is marked
│   ├── Investments/          public or private there
│   ├── Personal/
│   ├── Projects/
│   ├── Technical/
│   ├── Travel/
│   └── Other/
├── index.md                ← master table of contents (private)
└── log.md                  ← chronological activity record (private)
```
</directory_structure>

<domain_categories>
Top-level domains are broad categories. **They are NOT flat** — subfolders nest freely within them:
- `wiki/Technical/ML/attention-mechanisms.md`
- `wiki/Career/<company>/onboarding-notes.md`
- `wiki/Personal/Health/sleep-tracking.md`

<routing_guidance>
- **Career** — work, professional development, company-specific knowledge
- **Family** — family matters, relationships with family members
- **Investments** — personal finance, investing, and accounting concepts (e.g. Opex vs Capex)
- **Personal** — self-improvement, goals, health/healthcare, psychology, journal reflections
- **Projects** — side projects, hackathons, open-source work
- **Technical** — technical knowledge, concepts, tools, frameworks (not tied to a specific job)
- **Travel** — trips, destinations, planning, experiences
- **Other** — anything that doesn't fit above

Cross-domain linking is encouraged. A technical concept learned at work can link to both `wiki/Technical/` and `wiki/Career/`.
</routing_guidance>
</domain_categories>

<voice_and_editorial_rules>
The approach depends on the input quality and content type:

| Input type | Approach |
|---|---|
| Messy/garbled (typical of speech-to-text) | Synthesize and clean up substantially. Restructure for clarity. |
| Structured/organized | Preserve the owner's words mostly. Fix only errors. |
| Personal/emotional content | **Always** preserve voice and human meaning. Fix only surface-level errors (typos, grammar). Never rephrase emotional expression. |

**In all cases:**
- Auto-correct speech-to-text artifacts (homophones, garbled text, missing punctuation)
- Fix spelling and grammar errors
- Never change meaning or intent
- Never add content the owner didn't express

<inline_agent_directives>
The owner embeds inline instructions to Claude using an **`@Agent`** tag inside inbox notes — e.g. `@Agent transcribe this`, `@Agent clean up the table`, `@Agent add an example here`, `@Agent make this generic`, `@Agent curl this URL and …`. These are directives about how to process *that specific document*, usually placed right after the image, paragraph, or block they refer to.

- **Execute the instruction** while processing the note.
- **Never copy the `@Agent` line — or any paraphrase of it — into the wiki.** It is a message to Claude, not wiki content. Carry out the directive, then drop the marker entirely.
</inline_agent_directives>
</voice_and_editorial_rules>

<captured_links>
Inbox notes are full of bare URLs, and a captured URL means one of **two different things**. Read the surrounding note to tell which — the routing depends entirely on it.

**A to-do link** — the note is a bare link dump, or sits in a reading-list / "to read" / "to watch" context, with none of the owner's own notes around it. They haven't consumed it yet. This belongs on `wiki/Other/Reading List.md` with a substantive descriptor, and **must not** become a wiki page of its own: writing one from a source the owner hasn't read puts unvetted claims in their voice.

**A source link** — the link accompanies notes the owner has already written on the topic. They've read it, and the URL is there to (1) give you the context behind their notes and (2) be **preserved as attribution**, so the reference survives for future indexing. Here:

- Their notes are the substance of the page and their voice governs it. Use the fetched source to *disambiguate* garbled dictation, resolve half-finished thoughts, and sanity-check claims — not to pad the page with everything the article said. The `<voice_and_editorial_rules>` ban on adding content they didn't express still applies.
- **Keep the URL on the resulting page.** Use the established footer convention: a `---` rule, then `Source: <title/description>` with the link. Losing the reference is a real cost — it's half of why they captured it.
- If the source **contradicts** their notes, don't silently overwrite. Correct clear factual errors and say so in the session report; where it's genuinely ambiguous, note both readings.

In **both** cases:

- **WebFetch the URL.** Never file a bare link. For a to-do link, the fetch is what makes the reading-list entry say what the thing *is* — title, author, actual argument — so it's useful without opening it; a line that only repeats the slug has added nothing. For a source link, the fetch is what lets you process their notes accurately.
- **When a fetch fails, say so.** Paywalls, login walls, and robots-blocked domains are common — Reddit is blocked outright, LinkedIn and X usually are. Keep the bare link, note that it couldn't be fetched, and flag it in the session report. Never infer content from a URL slug.
- **Strip tracking parameters** (`utm_*`, `typeform-source`, referral/affiliate codes) while keeping the URL working. Never carry an affiliate link into the wiki — if a source is monetised, note that instead, because it bears on how much to trust it.
- **Instagram posts** go through the `process-instagram-source` skill instead — the content is in the slides, not the caption.
</captured_links>

<inbox_artifacts>
**`inbox/` accepts any file type, not just markdown.** A PDF, a photo of a whiteboard, a voice memo, a spreadsheet, an `.epub` — these are normal captures, not mistakes to be flagged. The capture zone is deliberately zero-friction: the owner drops in whatever form the thought arrived in, and processing is what turns it into a wiki page.

Two rules hold regardless of file type:

- **Extract, don't skip.** A non-markdown item gets processed like any other note — read it, pull out what matters, route it to a domain, archive the original. Never file an item you haven't opened, and never describe a file from its name alone. Guessing at the contents of `scan_004.pdf` is the same error as inferring an article from its URL slug.
- **Never fake an extraction.** If you can't open something — no tooling, a corrupt or encrypted file, illegible handwriting — say so plainly in the session report, leave the item unprocessed in `inbox/`, and ask. A confident summary of a file you couldn't actually read is far worse than an admission that you couldn't read it.

<file_type_handling>
| Type | Handling |
|---|---|
| **PDF** | Use the **`process-pdf`** skill. It splits into two very different cases: **scans/photos of the owner's handwritten notes** (transcribe them, crop the hand-drawn diagrams out and embed them) and **born-digital documents** (extract the text, treat as a source). |
| **Images** (photos, screenshots, whiteboards) | `Read` them and work from what you see. Whiteboards and slides get transcribed; a diagram worth keeping gets named and embedded per `<assets>`. Screenshots of text are content, not decoration. |
| **Audio / voice memos** | No transcription model is installed — `ffmpeg` can inspect and convert, but it cannot transcribe. Flag the item and ask rather than guessing from the filename. (`brew install whisper-cpp` plus a model would enable this; don't install it unasked.) |
| **Office docs** (`.docx`, `.xlsx`, `.pptx`, `.rtf`) | `pandoc <file> -t markdown` for prose; `textutil` (macOS built-in) as a fallback. Spreadsheets: pull the figures into a markdown table on the destination page — don't paste a dump. |
| **Ebooks** (`.epub`) | `pandoc` converts to markdown. These are almost always reading material, so the to-do-vs-source distinction in `<captured_links>` matters more than the conversion. |
| **Code / data** (`.py`, `.ipynb`, `.csv`, `.json`) | Usually a snippet the owner wants to keep, not a project. Put it in a fenced block on the relevant page with a sentence on why it's there. Notebooks: keep the code and conclusions, drop the noise. |
| **Archives** (`.zip`) | Extract to `/tmp`, list what's inside, and ask before processing the contents — an archive rarely maps to one page. |
| **Anything else** | Identify it (`file <path>`), try the obvious tool, and if that fails, flag it. `uv run --with <pkg>` and `brew install` are both available for a missing library. |
</file_type_handling>

<artifact_retention>
The wiki page is the durable record, but the source file is often worth keeping too:

- **Archive the original to `inbox/processed/`** (private) once processed — the default, exactly as for a markdown note. The collision rules in the `process-inbox` skill apply to binaries too.
- **Also preserve it in `assets/` and link it from the page when it's a lasting reference** — a paper, spec, statement, or guide worth reopening. Descriptive kebab-case name, explicit vault-root path, and a **plain `[[…]]` link rather than an `![[…]]` embed** for non-image files, since Obsidian renders an embedded PDF as a full inline viewer. Use the established source footer:

  ```markdown
  ---
  Source: Leviathan et al., "Fast Inference from Transformers via Speculative Decoding" — [[assets/public/speculative-decoding-paper.pdf]]
  ```

- **A transcribed handwritten scan needs no copy in `assets/`** — the transcription plus its cropped diagrams *is* the record. Archive the scan.
- **Privacy applies with more force to documents than to images.** `assets/public/` is committed to git and is only for files a **public** note references. Statements, payslips, letters, medical documents and anything carrying a name and address stay in private `assets/` — and if the page discussing one is itself sensitive, use the `.local.md` convention.
- **Free PDFs are often lead magnets.** The same rule as affiliate links holds: strip nothing from the owner's notes, but never carry a referral link into the wiki, and note that a source is monetised, because it bears on how much to trust it.
</artifact_retention>
</inbox_artifacts>

<conventions>
<file_naming>
- This governs wiki **pages** (`.md` files). Image and diagram files follow a different rule — descriptive **kebab-case** — see `<assets>`.
- Page file names use **title case with spaces** (e.g., `Installing JAX.md`, `Z-Score Normalization.md`)
- The file name IS the page title in Obsidian — **do not** add a `# Title` heading inside the file, as it creates duplication
- Content starts immediately after the frontmatter (or after a brief intro sentence, then `##` subheadings)
</file_naming>

<wiki_links>
Use `[[page-name]]` for cross-references. Use `[[page-name|display text]]` when the link text should differ.
</wiki_links>

<assets>
Images and diagrams are **private by default**: they live in `assets/` (gitignored) unless promoted to `assets/public/` (committed — assets for **public** notes only, i.e. notes in a domain the owner made public during `install-wiki`). See `<privacy_and_git>` for the public/private rule. `assets/` also holds **preserved source files** — a PDF kept as a lasting reference lives here under the same rules; see `<artifact_retention>`.

- **Embed with an explicit vault-root-relative path, never a bare filename.** Use `![[assets/public/kebab-name.png]]` for public imagery and `![[assets/kebab-name.png]]` for private. Size/alias modifiers still work: `![[assets/foo.svg|400]]`. The path — not filename resolution — is what points at the file, and it makes the public/private location explicit in the note. **Non-image assets take the same explicit path but a plain `[[…]]` link instead of an `![[…]]` embed** (`![[…pdf]]` renders an inline PDF viewer).
- **Private is the safe default, but prefer public when eligible.** New captures land in `assets/` (private); **promote an image to `assets/public/` whenever a note in a public domain embeds it — and only then.** Don't leave public-note imagery lingering in private `assets/` (it should be committed and backed up); equally, imagery for any private-domain note must stay private.
- **Name asset files in descriptive kebab-case** that says what the file *is* (e.g. `speculative-decoding-latency-speedup-chart.png`, `revolut-voice-state-machine.png`), never the capture artifact (`IMG_1265.jpeg`, `Pasted image 20260609203551.png`). Rename on ingest; if unsure what an image shows, open it and look before naming. Keep each basename unique across `assets/` (including `assets/public/`).
- **Whenever you rename or move an image, update its embed path in every note that references it — across BOTH `wiki/` and `inbox/` (including `inbox/processed/` and `inbox/public/`), not just the wiki.** A rename changes the filename; promoting between `assets/` and `assets/public/` changes the folder in the path. Because the path is explicit (not filename-resolved), a stale reference anywhere breaks. Grep the whole vault for the old `[[…name…]]` token to catch every occurrence.
</assets>

<frontmatter>
Wiki pages get light YAML frontmatter (hidden in Obsidian reading mode):
```yaml
---
date: 2026-05-16
domain: Technical
tags: [ml, transformers, attention]
---
```

Keep it minimal. Only `date`, `domain`, and `tags`. Don't over-tag.
</frontmatter>

<privacy_and_git>
- **The vault is private by default; git tracks only explicit public allowlists.** The `.gitignore` ignores everything and re-includes only the paths the owner chose to make public (plus root config like `.gitignore`, `package.json`, `.mcp.json`, `.claude/`, and `.agents/` — where the project skills live, with `.claude/skills` symlinked to it). Everything else stays private, synced only via the owner's cloud storage. This means a new top-level domain, a new asset, or a new inbox note is **private unless deliberately placed in a public location**.
- **Which domains are public** — `<to_be_determined_from_install_skill>`. `install-wiki` asks the owner which top-level `wiki/` domains should be committed and writes the corresponding allowlist into `.gitignore`. The rest are private. Until then, assume **everything is private** (the shipped `.gitignore` has no allowlist). A common choice is to make a `Technical/` domain public and keep personal domains private, but nothing is committed unless the owner opted it in.
- **Assets:** `assets/` is private (gitignored); only `assets/public/` is committed, and only imagery embedded by a **public** note belongs there. Everything else — private-note imagery, unreferenced captures — stays in `assets/` (private). Embeds use the explicit path (see `<assets>`), so an image's public/private location is visible in every note that references it.
- **Inbox:** `inbox/` is private (gitignored), including `inbox/processed/`. Only `inbox/public/` is committed — a git-synced drop zone for **public, non-personal notes** (e.g. captured on a work machine, then pulled and processed on a personal one). When processing an `inbox/public/` item, archive the original to the private `inbox/processed/` (so the public drop zone clears and the raw capture leaves git on the next push).
- **`.local.md` convention:** Any file ending in `.local.md` is never committed to git, regardless of location. Use this for sensitive notes that should stay private even within a public domain.
</privacy_and_git>

<index>
- `index.md` — human-browsable table of contents organized by domain
- Each entry: `[[wiki-link]]` — one-line description
- Update after every processing session
</index>

<log>
- `log.md` — append-only chronological record
- Format: `## [YYYY-MM-DD] action | description`
- Actions: `ingest`, `query`, `lint`, `update`
- Append after every processing session
</log>
</conventions>

<tooling>
<qmd>
qmd is the search engine, available via **MCP** (tools: `query`, `get`, `multi_get`, `status`) and **CLI** (`qmd` command).

- MCP for: single queries, drilling into pages, iterative search-then-read
- CLI for: bulk retrieval (`qmd multi-get "wiki/Technical/*.md"`), BM25-only speed (`qmd search "term"`), score debugging (`qmd query --explain`), piping/composing

After processing inbox items, always run `qmd update && qmd embed` to keep the index current.
</qmd>

<dataview>
Wiki pages have frontmatter compatible with Obsidian's Dataview plugin. The owner can create dashboard pages with live queries.
</dataview>
</tooling>

<skills>
- **When the owner wants to process/organize notes** → use `/process-inbox`
- **When the owner is querying/searching the wiki** → use `/query-wiki`
- **When the owner wants to health-check the wiki** → use `/lint-wiki`
- **When an inbox item is a PDF** → use `/process-pdf` (handwritten notes get transcribed and their diagrams cropped out), then carry on with `/process-inbox`
- **When an inbox note points at an Instagram image/carousel post** → use `/process-instagram-source` to extract it, then carry on with `/process-inbox`
- **When setting up this existing wiki on a new machine** → owner will invoke `/setup-existing-wiki` themselves
- **To create a brand-new wiki from the liki template** → `/install-wiki` (a one-time bootstrap; already run for this vault, but re-runnable or usable to help set up a friend)
</skills>
