#!/usr/bin/env python3
"""Shared helpers for the wiki→Anki pipeline (stdlib only, like the lint scripts).

Everything here is pure/markdown-side — no `anki` import — so it runs under
`/usr/bin/python3` and is used by both `mint_ids.py` and `card_audit.py`, and by
`anki_reconcile.py` (which adds the Anki-side work on top).

Contents:
  - the `## Anki Cards` parser (the grammar from the plan's §07)
  - deck-name mapping   (page path → `Wiki::…`)
  - the git-public gate (which pages may hold cards)
  - the `obsidian://` Source URI
  - LaTeX → MathJax and media-embed extraction
  - the markdown → Anki HTML field renderer (`render_field`)

Run directly for a self-test:
    /usr/bin/python3 .agents/skills/process-inbox/scripts/card_lib.py
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import unicodedata
import urllib.parse
from dataclasses import dataclass, field

# --- constants ---------------------------------------------------------------
DECK_ROOT = "Wiki"  # top-level Anki deck (template default; rename if you like)
CONTENT_ROOT = "wiki"  # the wiki/ content dir inside the vault root
MINT = "MINT"  # placeholder an LLM writes; mint_ids.py replaces it


def vault_name():
    """Obsidian vault name for obsidian:// links — the vault-root folder's basename
    (set WIKI_VAULT_NAME to override). Scripts are run from the vault root."""
    return os.environ.get("WIKI_VAULT_NAME") or os.path.basename(os.path.abspath("."))


SECTION_RE = re.compile(r"^##\s+Anki\s+Cards\s*$")
HEADING_RE = re.compile(r"^#{1,2}\s")  # a `#`/`##` heading ends the section
ULID_RE = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}")  # Crockford base32, 26 chars

_MARKER = re.compile(r"^>\s*\[!card\][+-]?\s*(.*)$")  # `> [!card]`/`-`/`+` <front>
_CONT = re.compile(r"^>\s?(.*)$")  # any `>` continuation line
_IDLINE = re.compile(r"^>\s*<!--\s*anki:\s*(\S+)\s*-->\s*$")  # `> <!-- anki: <id> -->`


# --- parser ------------------------------------------------------------------
@dataclass
class Card:
    id: str  # a 26-char ULID, or the MINT placeholder
    front: str
    back: str
    start: int  # 0-based line index of the `[!card]` marker
    end: int  # 0-based line index of the id-comment line


@dataclass
class ParseResult:
    cards: list = field(default_factory=list)  # well-formed ULID cards
    placeholders: list = field(default_factory=list)  # id == MINT, awaiting mint
    errors: list = field(default_factory=list)  # "path:line: message"
    has_section: bool = False


def _section_bounds(lines):
    """Return (start, end) line indices of the `## Anki Cards` body, or None.

    `start` is the first line *after* the heading; `end` is exclusive (the next
    `#`/`##` heading, or EOF). A second `## Anki Cards` heading is an error.
    """
    heads = [i for i, ln in enumerate(lines) if SECTION_RE.match(ln)]
    if not heads:
        return None, None, None
    if len(heads) > 1:
        return heads[0] + 1, len(lines), heads  # caller flags the duplicates
    start = heads[0] + 1
    end = len(lines)
    for i in range(start, len(lines)):
        if HEADING_RE.match(lines[i]):
            end = i
            break
    return start, end, heads


def parse_cards(text, path="<mem>"):
    """Parse the `## Anki Cards` section of one page into a ParseResult."""
    res = ParseResult()
    lines = text.splitlines()
    start, end, heads = _section_bounds(lines)
    if start is None:
        return res  # no section — not an error, just no cards
    res.has_section = True
    if heads and len(heads) > 1:
        for h in heads[1:]:
            res.errors.append(f"{path}:{h + 1}: duplicate `## Anki Cards` heading")

    i = start
    while i < end:
        line = lines[i]
        m = _MARKER.match(line)
        if not m:
            # A stray id-comment outside any card block is the classic mis-parse
            # symptom (an LLM reflowed the callout). Make it loud.
            if _IDLINE.match(line):
                res.errors.append(
                    f"{path}:{i + 1}: `<!-- anki: … -->` outside a [!card] block"
                )
            i += 1
            continue

        front = m.group(1).strip()
        back_lines = []
        card_id = None
        block_end = None
        j = i + 1
        while j < end:
            idm = _IDLINE.match(lines[j])
            if idm:
                card_id = idm.group(1)
                block_end = j
                j += 1
                break
            if _MARKER.match(lines[j]):
                break  # next card started before this one closed
            cm = _CONT.match(lines[j])
            if cm is None:
                break  # a non-`>` line ends the callout
            back_lines.append(cm.group(1))
            j += 1

        if card_id is None:
            res.errors.append(
                f"{path}:{i + 1}: [!card] block has no `<!-- anki: … -->` id line"
            )
            i = j
            continue

        card = Card(
            id=card_id,
            front=front,
            back="\n".join(back_lines).strip(),
            start=i,
            end=block_end,
        )
        if not front:
            res.errors.append(
                f"{path}:{i + 1}: [!card] has an empty front (no question)"
            )
        if not card.back:
            res.errors.append(f"{path}:{i + 1}: [!card] has an empty back (no answer)")
        if card_id == MINT:
            res.placeholders.append(card)
        elif ULID_RE.fullmatch(card_id):
            res.cards.append(card)
        else:
            res.errors.append(
                f"{path}:{block_end + 1}: malformed id '{card_id}' (not a 26-char ULID or {MINT})"
            )
        i = j

    return res


# --- deck mapping ------------------------------------------------------------
def deck_for_page(path):
    """`wiki/Domain/Sub/Some Page.md` → `Wiki::Domain::Sub`
    (the folder path under wiki/, not the filename)."""
    parts = path.replace(os.sep, "/").split("/")
    folders = parts[1:-1] if parts and parts[0] == CONTENT_ROOT else parts[:-1]
    return "::".join([DECK_ROOT] + folders)


# --- obsidian:// Source URI --------------------------------------------------
def source_uri(path, vault=None):
    """A back-link to the page. `file` is the vault-root-relative path (keeps the
    inner `wiki/`), url-encoded, extension dropped. The `vault` component is
    url-encoded too — vault folder names can contain spaces (`My Vault`), which
    would otherwise produce an invalid `obsidian://` URI. `vault` defaults to
    vault_name()."""
    rel = path.removesuffix(".md")
    enc = urllib.parse.quote(rel.replace(os.sep, "/"), safe="")
    vault_enc = urllib.parse.quote(vault or vault_name(), safe="")
    return f"obsidian://open?vault={vault_enc}&file={enc}"


# --- git-public gate ---------------------------------------------------------
def public_pages(paths, cwd="."):
    """Return the subset of `paths` that are card-eligible: committed to git
    (not ignored) and not a `*.local.md` file. Mirrors asset_audit.py's method —
    `git check-ignore` — so it needs no hardcoded domain name.

    Runs with `-z` (NUL-delimited I/O) and `core.quotePath=false` so a non-ASCII
    page path (e.g. `wiki/Café.md`) still string-matches the input. Without this,
    git C-quotes such paths in its output (`"wiki/Caf\\303\\251.md"`), the match
    fails, and a genuinely-private page would be classified public — a privacy
    gate must fail *closed*, not open."""
    candidates = [p for p in paths if not p.endswith(".local.md")]
    if not candidates:
        return set()
    proc = subprocess.run(
        ["git", "-c", "core.quotePath=false", "check-ignore", "-z", "--stdin"],
        input="".join(p + "\0" for p in candidates),
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if proc.returncode not in (0, 1):  # 0 = some ignored, 1 = none; else real error
        raise RuntimeError(
            "git check-ignore failed (run from the repo):\n" + proc.stderr
        )
    ignored = {s for s in proc.stdout.split("\0") if s}
    return {p for p in candidates if p not in ignored}


# --- field transforms --------------------------------------------------------
_BLOCK_MATH = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
# Inline math, pandoc-style: the opening `$` isn't followed by whitespace, the
# closing `$` isn't preceded by whitespace and isn't followed by a digit. That
# last rule keeps currency out — `from $5 to $20` is not math. Not DOTALL, so an
# inline span can't swallow a newline.
_INLINE_MATH = re.compile(r"(?<![\$\\])\$(?!\$)(?!\s)(.+?)(?<![\s\$\\])\$(?!\$)(?!\d)")
# Any `![[assets/…]]` embed: an optional `#fragment` and an optional `|modifier`
# (a size like `300` / `300x200`, or alt text). Matching every variant — not just
# a bare `|NNN` — is what lets find_media see (and the privacy guard reject) a
# private embed written with a modifier, and keeps modifier'd public embeds from
# being escaped into a card as broken literal text.
_EMBED = re.compile(
    r"!\[\[\s*(assets/(?:public/)?[^\]|#]+?)\s*(?:#[^\]|]*)?\s*(?:\|\s*([^\]]*?)\s*)?\]\]"
)


def _embed_width(modifier):
    """Pixel width from an embed modifier (`300` or `300x200` → `300`), else ''."""
    m = re.match(r"\d+", modifier or "")
    return m.group(0) if m else ""


def latex_to_mathjax(s):
    """`$$…$$` → `\\[…\\]` (block) and `$…$` → `\\(…\\)` (inline). Block first."""
    s = _BLOCK_MATH.sub(lambda m: r"\[" + m.group(1) + r"\]", s)
    s = _INLINE_MATH.sub(lambda m: r"\(" + m.group(1) + r"\)", s)
    return s


@dataclass
class MediaRef:
    token: str  # the whole `![[…]]` match, for substitution
    asset: str  # vault-relative path, e.g. "assets/public/foo.png"
    width: str  # the |NNN size, or ""
    public: bool  # under assets/public/ (only these may enter the collection)


def find_media(s):
    """Extract every `![[assets/…]]` embed as a MediaRef (no I/O)."""
    out = []
    for mt in _EMBED.finditer(s):
        asset = mt.group(1).strip()
        # Normalize before the public-prefix test so a traversal path such as
        # `assets/public/../../private/x.pdf` can't masquerade as public and leak
        # a private file into the collection.
        norm = os.path.normpath(asset).replace(os.sep, "/")
        out.append(
            MediaRef(
                token=mt.group(0),
                asset=asset,
                width=_embed_width(mt.group(2)),
                public=(norm == "assets/public" or norm.startswith("assets/public/")),
            )
        )
    return out


def render_field(text):
    """Render one card Front/Back into an Anki HTML field.

    LaTeX → MathJax and `![[assets/…]]` → `<img>` are rendered first and stashed
    behind NUL sentinels; the remaining prose is HTML-escaped, so stray `<`, `>`,
    `&` in prose (`A < B`, `<EOS>`, `List<T>`) render literally instead of being
    swallowed as markup; intra-line whitespace is collapsed while line breaks
    become `<br>`; then the rendered math/img is restored verbatim. NFC-normalized
    to match Anki's canonical field form, which avoids spurious updates when a page
    carries non-NFC text (common from speech-to-text capture)."""
    saved = []

    def stash(rendered):
        saved.append(rendered)
        return f"\x00{len(saved) - 1}\x00"

    s = _BLOCK_MATH.sub(lambda m: stash(r"\[" + m.group(1) + r"\]"), text)
    s = _INLINE_MATH.sub(lambda m: stash(r"\(" + m.group(1) + r"\)"), s)

    def _img(m):
        width = _embed_width(m.group(2))
        w = f' width="{width}"' if width else ""
        return stash(f'<img src="{os.path.basename(m.group(1).strip())}"{w}>')

    s = _EMBED.sub(_img, s)
    s = html.escape(s, quote=False)  # prose only — math/img are stashed away
    # collapse intra-line whitespace but keep line breaks as <br>: Anki renders
    # fields as HTML, so a bare newline would vanish and mash a multi-line back
    # onto one line.
    s = "<br>".join(" ".join(line.split()) for line in s.split("\n"))
    for i, rendered in enumerate(saved):
        s = s.replace(f"\x00{i}\x00", rendered)
    return unicodedata.normalize("NFC", s)


# --- self-test ---------------------------------------------------------------
_SAMPLE = """---
domain: Example
---

Some prose with inline $x^2$ and a block:

$$ E = mc^2 $$

## Anki Cards

> [!card]- What is the capital of France?
> Paris.
> <!-- anki: 01ARZ3NDEKTSV4RRFFQ69G5FAV -->

> [!card]+ Which placeholder does mint_ids replace?
> The MINT token, with a freshly generated ULID.
> <!-- anki: MINT -->

> [!card]- A malformed one with no id
> This block never closes with an id comment.

> <!-- anki: 01BX5ZZKBKACTAV9WEVGEMMVRZ -->
"""


def _self_test():
    ok = True

    def eq(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print(
            f"  [{'ok' if good else 'FAIL'}] {name}: {got!r}"
            + ("" if good else f"  != {want!r}")
        )

    print("parse_cards:")
    r = parse_cards(_SAMPLE, "sample.md")
    eq("has_section", r.has_section, True)
    eq("well-formed count", len(r.cards), 1)
    eq("placeholder count", len(r.placeholders), 1)
    eq("first card id", r.cards[0].id, "01ARZ3NDEKTSV4RRFFQ69G5FAV")
    # the placeholder card uses the expanded `[!card]+` fold marker
    eq("placeholder is MINT", r.placeholders[0].id, MINT)
    eq(
        "`[!card]+` parses (front captured)",
        r.placeholders[0].front.startswith("Which"),
        True,
    )
    # two errors: the id-less block, and the stray trailing id-comment
    eq("error count", len(r.errors), 2)
    print("     errors:", r.errors)
    eb = parse_cards(
        "## Anki Cards\n> [!card]- Q only?\n> <!-- anki: 01ARZ3NDEKTSV4RRFFQ69G5FAV -->\n",
        "eb.md",
    )
    eq("empty back flagged", len(eb.errors) == 1 and "empty back" in eb.errors[0], True)

    print("deck_for_page:")
    eq("nested", deck_for_page("wiki/Domain/Sub/Some Page.md"), "Wiki::Domain::Sub")
    eq("top-level", deck_for_page("wiki/Domain/Some Page.md"), "Wiki::Domain")

    print("source_uri:")
    eq(
        "encodes path",
        source_uri("wiki/Domain/Some Page.md", vault="wiki"),
        "obsidian://open?vault=wiki&file=wiki%2FDomain%2FSome%20Page",
    )
    eq(
        "encodes vault name with spaces",
        source_uri("wiki/A.md", vault="My Vault"),
        "obsidian://open?vault=My%20Vault&file=wiki%2FA",
    )

    print("latex_to_mathjax:")
    eq("inline+block", latex_to_mathjax(r"a $x$ and $$y$$ b"), r"a \(x\) and \[y\] b")

    print("find_media:")
    refs = find_media(
        "see ![[assets/public/chart.png|300]] and ![[assets/private.png]]"
    )
    eq("count", len(refs), 2)
    eq("public flag", (refs[0].public, refs[1].public), (True, False))
    eq("width", refs[0].width, "300")
    trav = find_media("![[assets/public/../../private/secret.pdf]]")
    eq("traversal is NOT public", trav[0].public, False)
    mods = find_media(
        "![[assets/public/a.png|400x300]] ![[assets/public/b.png|a caption]] "
        "![[assets/private/c.png|thumb]]"
    )
    eq("modifier'd embeds all matched", len(mods), 3)
    eq("WxH width parsed", mods[0].width, "400")
    eq("alt-text width is empty", mods[1].width, "")
    eq("private w/ modifier still NOT public", mods[2].public, False)

    print("render_field:")
    eq(
        "latex+media",
        render_field("a $x$ ![[assets/public/c.png|20]]"),
        'a \\(x\\) <img src="c.png" width="20">',
    )
    eq(
        "escapes stray html in prose",
        render_field("if A < B and x>0 & done"),
        "if A &lt; B and x&gt;0 &amp; done",
    )
    eq(
        "does not escape inside math",
        render_field("$a < b$"),
        r"\(a < b\)",
    )
    eq(
        "currency is not math",
        render_field("costs from $5 to $20 a month"),
        "costs from $5 to $20 a month",
    )
    eq(
        "line breaks become <br>",
        render_field("First line.\nSecond line."),
        "First line.<br>Second line.",
    )

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _self_test() else 1)
