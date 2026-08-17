---
name: query-wiki
description: Search and answer questions from the wiki knowledge base. Use when the user is asking about something that may be in their notes, or wants to find/synthesize information from the wiki.
---

# Query Wiki

You are searching and synthesizing answers from the user's wiki knowledge base.

## Workflow

### 1. Search

Use qmd to find relevant pages:
- **MCP tools** (default): `query` for semantic search, `get` to retrieve specific pages, `multi_get` for batch retrieval
- **CLI** (when needed):
  - Bulk retrieval: `qmd multi-get "wiki/Technical/*.md"` to load an entire domain
  - BM25-only for speed on exact keywords: `qmd search "exact term"`
  - Debugging relevance: `qmd query --explain "topic"` for score traces
  - Piping/composing: combining search results with shell operations

If qmd is unavailable, fall back to reading `index.md` and using Grep/Glob to find relevant pages.

### 2. Read

Read the relevant wiki pages to get full context. Don't just rely on snippets from search results.

### 3. Synthesize

Produce a clear, human-readable answer:
- Cite sources with `[[wiki-links]]` so the user can navigate to them in Obsidian
- If multiple pages are relevant, synthesize across them
- Be concise — the user wants answers, not summaries of what you found

### 4. Optionally File

If your answer represents a valuable synthesis (a comparison, a new connection, an analysis), offer to file it as a new wiki page. Only offer — don't do it without consent.

If filed, update `index.md`, `log.md`, and run `qmd update && qmd embed`.
