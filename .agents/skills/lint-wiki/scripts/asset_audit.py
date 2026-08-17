#!/usr/bin/env python3
"""Asset hygiene check: privacy routing, embed paths, names, and references.

Run from the vault root:

    /usr/bin/python3 .agents/skills/lint-wiki/scripts/asset_audit.py

Why this is a script and not a shell pipeline: the obvious `git ls-files
--others --exclude-standard -- assets/` cannot see private assets at all,
because `assets/` is gitignored and `--exclude-standard` filters out exactly
the files the audit exists to check. Enumerating with a filesystem walk avoids
that trap entirely. (If you do reach for a shell grep here, note that this
session's `grep` is a wrapper around `ugrep --ignore-files`, which honours
.gitignore and so silently finds nothing in the private trees — use
`rg --no-ignore` or `/usr/bin/grep`.)

Rules enforced (see <assets> and <privacy_and_git> in AGENTS.md):
  - assets/public/ is for assets referenced by PUBLIC-domain notes, and only those
  - everything else stays in the private assets/ root
  - references use explicit vault-root paths, never bare filenames
  - asset files use descriptive kebab-case names

"Asset" means any file under assets/, not just imagery: preserved source
documents (PDFs kept as lasting references) live there too and are linked rather
than embedded. See <artifact_retention> in AGENTS.md.

LIMITATION (liki template): the leak/promote logic below keys on the literal
domain name "Technical" as the public domain — the template author's setup. If
your public domain(s) differ (you chose them during install-wiki), edit the
"Technical" checks in main() to match, or replace them with a git-tracked test
(`git check-ignore <note>` → private). Until then, run this audit with that
caveat in mind; it will mis-classify assets tied to a non-Technical public domain.
"""

import collections
import os
import re
import sys

# Matches embeds (![[…]]) and plain links ([[…]]) alike, capturing the leading
# "!" so the two can be told apart. Both count as references to an asset: images
# are embedded, but non-image assets such as a preserved source PDF are *linked*
# (an ![[…pdf]] embed renders a full inline viewer in Obsidian), and counting
# only embeds would report every linked PDF as unreferenced.
REF = re.compile(r"(!?)\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]")
CRYPTIC = re.compile(r"IMG_|Pasted image|^DSC|^Screenshot|^image\d*\.", re.IGNORECASE)
NOTE_ROOTS = ("wiki", "inbox")


def main():
    if not os.path.isdir("assets") or not os.path.isdir("wiki"):
        sys.exit("error: run this from the vault root")

    assets = [
        os.path.join(r, f)
        for r, _d, fs in os.walk("assets")
        for f in fs
        if not f.startswith(".")
    ]

    refs = collections.defaultdict(list)  # 'assets/...' token -> [note paths]
    bare = []  # (note, token) for bare-filename embeds
    for base in NOTE_ROOTS:
        for root, _dirs, files in os.walk(base):
            for f in files:
                if not f.endswith(".md"):
                    continue
                note = os.path.join(root, f)
                for bang, tok in REF.findall(open(note, encoding="utf-8").read()):
                    tok = tok.strip()
                    if tok.startswith("assets/"):
                        refs[tok].append(note)
                    elif bang:
                        # A bare *embed* is a broken asset reference. A bare plain
                        # link is just an ordinary [[page-name]] wiki link.
                        bare.append((note, tok))

    findings = collections.OrderedDict()

    findings["BARE-FILENAME EMBEDS (rewrite to an explicit assets/ path)"] = [
        f"{n}  ->  ![[{t}]]" for n, t in bare
    ]
    findings["EMBEDS POINTING AT A MISSING FILE"] = [
        f"{t}  <- {', '.join(n)}"
        for t, n in sorted(refs.items())
        if not os.path.exists(t)
    ]

    leaks, unref_public, promote, dead, inbox_only = [], [], [], [], []
    for a in sorted(assets):
        notes = refs.get(a, [])
        wiki_domains = sorted({n.split("/")[1] for n in notes if n.startswith("wiki/")})
        if a.startswith("assets/public/"):
            if not notes:
                unref_public.append(a)
            elif not wiki_domains:
                leaks.append(f"{a} -> referenced only by inbox: {', '.join(notes)}")
            elif wiki_domains != ["Technical"]:
                leaks.append(f"{a} -> embedded by {', '.join(wiki_domains)}")
        else:
            tech = [n for n in notes if n.startswith("wiki/Technical/")]
            if tech:
                promote.append(f"{a} -> embedded by {', '.join(tech)}")
            elif not notes:
                dead.append(a)
            elif not wiki_domains:
                inbox_only.append(f"{a} -> only in {', '.join(notes)}")

    findings["PRIVACY LEAKS (in assets/public/ but not Technical-only)"] = leaks
    findings["UNREFERENCED PUBLIC ASSETS (demote to private assets/)"] = unref_public
    findings["SHOULD BE PROMOTED (private, but a Technical note embeds it)"] = promote
    findings["CRYPTIC NAMES (rename to descriptive kebab-case)"] = [
        a for a in assets if CRYPTIC.search(os.path.basename(a))
    ]

    counts = collections.Counter(os.path.basename(a) for a in assets)
    findings["DUPLICATE BASENAMES across assets/ and assets/public/"] = [
        f"{b}: {[a for a in assets if os.path.basename(a) == b]}"
        for b, c in counts.items()
        if c > 1
    ]

    # Informational: these are usually deliberate. Do not report as defects
    # without checking log.md — past lints have explicitly accepted some.
    findings["(info) PRIVATE ASSETS WITH NO REFERENCE ANYWHERE"] = dead
    findings["(info) PRIVATE ASSETS REFERENCED ONLY BY INBOX NOTES"] = inbox_only

    problems = 0
    for title, items in findings.items():
        print(f"=== {title} ({len(items)}) ===")
        for i in items:
            print(f"    {i}")
        if not items:
            print("    (none)")
        print()
        if not title.startswith("(info)"):
            problems += len(items)

    print(f"summary: {len(assets)} assets, {problems} actionable finding(s)")


if __name__ == "__main__":
    main()
