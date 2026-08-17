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
  - assets/public/ is for assets referenced by PUBLIC (committed) notes, and only those
  - everything else stays in the private assets/ root
  - references use explicit vault-root paths, never bare filenames
  - asset files use descriptive kebab-case names

"Asset" means any file under assets/, not just imagery: preserved source
documents (PDFs kept as lasting references) live there too and are linked rather
than embedded. See <artifact_retention> in AGENTS.md.
"""

import collections
import os
import re
import subprocess
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

    # Classify each referencing note as public (committed) or private (gitignored).
    # "Public" is defined by git — a note is public iff git does not ignore it — so the
    # audit works for ANY choice of public domains, with no hardcoded domain name.
    # See <privacy_and_git> in AGENTS.md.
    all_ref_notes = sorted({n for notes in refs.values() for n in notes})
    private_notes = set()
    if all_ref_notes:
        proc = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            input="\n".join(all_ref_notes),
            capture_output=True,
            text=True,
        )
        # 0 = some paths ignored, 1 = none ignored; anything else is a real failure
        # (e.g. not inside a git repo), which would silently mark every note "public".
        if proc.returncode not in (0, 1):
            sys.exit(
                "error: `git check-ignore` failed — run this from inside the git repo.\n"
                + proc.stderr.strip()
            )
        private_notes = {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}

    def split_refs(notes):
        pub = [n for n in notes if n not in private_notes]
        priv = [n for n in notes if n in private_notes]
        return pub, priv

    leaks, unref_public, promote, dead, private_only = [], [], [], [], []
    for a in sorted(assets):
        notes = refs.get(a, [])
        pub, priv = split_refs(notes)
        if a.startswith("assets/public/"):
            # Committed and world-readable — legitimate only if a public note uses it.
            if not notes:
                unref_public.append(a)
            elif not pub:
                leaks.append(
                    f"{a} -> referenced only by PRIVATE notes: {', '.join(priv)}"
                )
            # else: at least one public note references it -> correctly public
        else:
            # Private asset. A public note embedding it means the committed repo has a
            # broken embed, and the asset should be promoted to assets/public/.
            if pub:
                promote.append(f"{a} -> embedded by public note(s): {', '.join(pub)}")
            elif not notes:
                dead.append(a)
            else:
                private_only.append(f"{a} -> only in {', '.join(priv)}")

    findings[
        "PRIVACY LEAKS (in assets/public/ but referenced only by private notes)"
    ] = leaks
    findings["UNREFERENCED PUBLIC ASSETS (demote to private assets/)"] = unref_public
    findings["SHOULD BE PROMOTED (private asset embedded by a public note)"] = promote
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
    findings["(info) PRIVATE ASSETS REFERENCED ONLY BY PRIVATE NOTES"] = private_only

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
