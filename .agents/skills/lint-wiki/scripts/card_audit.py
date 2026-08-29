#!/usr/bin/env python3
"""Card-health checks for /lint-wiki. Reports only — never fixes (lint's rule).

Two layers (plan §13):
  - markdown-structure (stdlib): duplicate ids, unminted MINT, malformed blocks,
    a `## Anki Cards` section on a non-public/.local page (privacy).
  - Anki-cross (needs the notes table): stale, hand-edited, orphaned. These need
    the pinned venv, so pass --with-anki and run under uv.

    /usr/bin/python3 .agents/skills/lint-wiki/scripts/card_audit.py            # markdown only
    uv run --with anki==<anki-version> python .agents/skills/lint-wiki/scripts/card_audit.py --with-anki
    /usr/bin/python3 .agents/skills/lint-wiki/scripts/card_audit.py --self-test
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "process-inbox",
        "scripts",
    ),
)
import card_lib  # noqa: E402

MANAGED_TAG = "wiki::synced"
ORPHAN_TAG = "wiki::orphaned"


def find_pages(vault="."):
    pages = []
    for dp, _d, fs in os.walk(os.path.join(vault, "wiki")):
        for f in fs:
            if f.endswith(".md"):
                pages.append(os.path.relpath(os.path.join(dp, f), vault))
    return sorted(pages)


def scan_markdown(pages_text, public):
    """pages_text: {path: text}; public: set of card-eligible paths. Pure."""
    out = {"malformed": [], "unminted": [], "duplicate": [], "privacy": []}
    locs = {}  # ulid -> [paths]
    for path, text in pages_text.items():
        pr = card_lib.parse_cards(text, path)
        out["malformed"].extend(pr.errors)
        for c in pr.placeholders:
            out["unminted"].append(
                f"{path}:{c.start + 1}: MINT placeholder — run mint_ids.py"
            )
        if pr.has_section and path not in public:
            out["privacy"].append(
                f"{path}: has `## Anki Cards` but is not git-public / is .local — must not exist"
            )
        for c in pr.cards:
            locs.setdefault(c.id, []).append(path)
    for ulid, where in sorted(locs.items()):
        if len(where) > 1:
            out["duplicate"].append(f"{ulid}: on {', '.join(where)}")
    return out


def scan_anki(vault_ulids, col):
    """vault_ulids: {ulid: (page, page_mtime)}. Needs an open collection."""
    out = {"orphaned": [], "hand_edited": [], "stale": []}
    managed = {}  # guid -> note
    for nid in col.find_notes(f"tag:{MANAGED_TAG}"):
        n = col.get_note(nid)
        managed[n.guid] = n
    for gid, note in managed.items():
        if gid not in vault_ulids and ORPHAN_TAG not in note.tags:
            out["orphaned"].append(
                f"{gid}: in Anki (wiki::synced) but no card in the vault — pending suspend"
            )
    for ulid, (page, mtime) in vault_ulids.items():
        if ulid not in managed:
            out["hand_edited"].append(
                f"{ulid} ({page}): matches no note in Anki — a new unsynced card or a hand-edited id"
            )
        elif mtime > managed[ulid].mod:  # note.mod is epoch seconds
            out["stale"].append(
                f"{ulid} ({page}): page modified after last sync — answer may be stale"
            )
    return out


_TITLES = {
    "malformed": "MALFORMED CARD BLOCKS (won't parse to (id, front, back))",
    "unminted": "UNMINTED PLACEHOLDERS (MINT left in place)",
    "duplicate": "DUPLICATE IDS (same ULID on 2+ blocks)",
    "privacy": "PRIVACY (cards section on a non-public page)",
    "orphaned": "ORPHANED IN ANKI (pending suspend)",
    "hand_edited": "UNKNOWN IDS (new-unsynced or hand-edited)",
    "stale": "STALE ANSWERS (page changed after last sync)",
}


def _report(findings):
    problems = 0
    for key, items in findings.items():
        print(f"=== {_TITLES[key]} ({len(items)}) ===")
        for i in items:
            print(f"    {i}")
        if not items:
            print("    (none)")
        print()
        problems += len(items)
    print(f"summary: {problems} card-health finding(s)")
    return problems


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-anki", action="store_true")
    ap.add_argument("--collection")
    ap.add_argument("--profile", default="Wiki")
    ap.add_argument("--vault", default=".")
    a = ap.parse_args(argv[1:])

    pages = find_pages(a.vault)
    pages_text = {
        p: open(os.path.join(a.vault, p), encoding="utf-8").read() for p in pages
    }
    public = card_lib.public_pages(pages, cwd=a.vault)
    findings = scan_markdown(pages_text, public)

    if a.with_anki:
        from anki.collection import Collection

        col_path = a.collection or os.path.expanduser(
            f"~/Library/Application Support/Anki2/{a.profile}/collection.anki2"
        )
        vault_ulids = {}
        for p in sorted(public):
            mtime = os.path.getmtime(os.path.join(a.vault, p))
            for c in card_lib.parse_cards(pages_text[p], p).cards:
                vault_ulids[c.id] = (p, mtime)
        col = Collection(col_path)
        try:
            findings.update(scan_anki(vault_ulids, col))
        finally:
            col.close()

    return 0 if _report(findings) == 0 else 1


# --- self-test (markdown layer; anki layer uses reconcile-verified primitives) ---
def _self_test():
    ok = True

    def want(name, cond):
        nonlocal ok
        ok = ok and cond
        print(f"  [{'ok' if cond else 'FAIL'}] {name}")

    A = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    card = lambda front, cid: f"> [!card]- {front}\n> ans\n> <!-- anki: {cid} -->\n"
    p1 = "## Anki Cards\n\n" + card("q1", A) + "\n" + card("q2", "MINT")
    p2 = "## Anki Cards\n\n" + card("dup", A) + "\n> [!card]- no id here\n> body\n"
    p3 = "## Anki Cards\n\n" + card("private", "01BX5ZZKBKACTAV9WEVGEMMVRZ")
    pages_text = {"wiki/Pub/p1.md": p1, "wiki/Pub/p2.md": p2, "wiki/Priv/p3.md": p3}
    public = {"wiki/Pub/p1.md", "wiki/Pub/p2.md"}  # p3 is private

    f = scan_markdown(pages_text, public)
    want("1 unminted (MINT on p1)", len(f["unminted"]) == 1)
    want("1 malformed (id-less block on p2)", len(f["malformed"]) == 1)
    want(
        "1 duplicate (A on p1+p2)", len(f["duplicate"]) == 1 and A in f["duplicate"][0]
    )
    want(
        "1 privacy (p3 not public)",
        len(f["privacy"]) == 1 and "p3.md" in f["privacy"][0],
    )
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        sys.exit(0 if _self_test() else 1)
    sys.exit(main(sys.argv))
