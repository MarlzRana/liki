#!/usr/bin/env python3
"""Reconcile the vault's `## Anki Cards` into a local Anki collection.

The deterministic half of the pipeline. Reads every git-public page's cards,
diffs against the notes tagged `wiki::synced`, and makes the collection match:
add new, update changed, move on folder change, suspend-and-tag orphans (never
delete). `--dry-run` computes and prints the diff without opening for mutation.

Needs the pinned anki backend, so run under uv:
    uv run --with anki==<anki-version> python .agents/skills/process-inbox/scripts/anki_reconcile.py --dry-run
    uv run --with anki==<anki-version> python .agents/skills/process-inbox/scripts/anki_reconcile.py --self-test

Identity is `note.guid` = the card ULID, matched via an in-memory map built from
the one `tag:wiki::synced` query (guid: is not a search filter — see the plan).
"""

from __future__ import annotations

import argparse
import os
import sys
import unicodedata
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import card_lib  # noqa: E402

NOTETYPE = "Wiki Card"
MANAGED_TAG = "wiki::synced"
ORPHAN_TAG = "wiki::orphaned"
FIELDS = ["Front", "Back", "WikiID", "Source"]
QUEUE_SUSPENDED = -1


# --- markdown side -----------------------------------------------------------
def render_field(text):
    """Markdown → an Anki field: LaTeX→MathJax, media embeds → <img>, flatten.

    (TODO for the dogfood: HTML-escape stray < > & in prose; ML answers rarely
    contain them, and escaping interacts with the injected <img>/MathJax.)"""
    s = card_lib.latex_to_mathjax(text)
    for ref in card_lib.find_media(text):
        w = f' width="{ref.width}"' if ref.width else ""
        s = s.replace(ref.token, f'<img src="{os.path.basename(ref.asset)}"{w}>')
    # NFC to match Anki's canonical field form — avoids spurious updates when a
    # page carries non-NFC text (common from speech-to-text capture).
    return unicodedata.normalize("NFC", " ".join(s.split()))


def build_records(pages, vault_root):
    """Parse each public page → {ulid: record}. Collects every error; the caller
    aborts the whole run if any exist (loud-fail, plan §07)."""
    records, errors = {}, []
    for page in pages:
        text = open(os.path.join(vault_root, page), encoding="utf-8").read()
        pr = card_lib.parse_cards(text, page)
        errors.extend(pr.errors)
        for c in pr.placeholders:
            errors.append(
                f"{page}:{c.start + 1}: unminted MINT placeholder — run mint_ids.py"
            )
        deck, source = card_lib.deck_for_page(page), card_lib.source_uri(page)
        for c in pr.cards:
            if c.id in records:
                errors.append(
                    f"{page}: duplicate id {c.id} (also on {records[c.id]['page']})"
                )
                continue
            media = card_lib.find_media(c.front + "\n" + c.back)
            for m in media:
                if not m.public:
                    errors.append(
                        f"{page}: card {c.id} embeds PRIVATE asset {m.asset} "
                        "— refusing to put private content in a public card"
                    )
            records[c.id] = {
                "front": render_field(c.front),
                "back": render_field(c.back),
                "deck": deck,
                "source": source,
                "page": page,
                "media": [m for m in media if m.public],
            }
    return records, errors


# --- plan --------------------------------------------------------------------
@dataclass
class Plan:
    add: list = field(default_factory=list)  # (ulid, deck, front)
    update: list = field(default_factory=list)  # (ulid, page)
    move: list = field(default_factory=list)  # (ulid, from_deck, to_deck)
    noop: list = field(default_factory=list)  # ulid
    resurrect: list = field(
        default_factory=list
    )  # ulid — was orphaned, now back in the vault
    suspend: list = field(default_factory=list)  # (ulid, source)
    blocked: bool = False  # orphan guard tripped


def compute_plan(col, records):
    """Read the collection and diff against records. No mutation."""
    plan = Plan()
    anki = {}  # guid -> (note, current_deck_name, is_orphaned)
    for nid in col.find_notes(f"tag:{MANAGED_TAG}"):
        note = col.get_note(nid)
        cids = note.card_ids()
        deck = col.decks.name(col.get_card(cids[0]).did) if cids else ""
        anki[note.guid] = (note, deck, ORPHAN_TAG in note.tags)

    wiki_ids, anki_ids = set(records), set(anki)
    for gid in sorted(wiki_ids - anki_ids):
        r = records[gid]
        plan.add.append((gid, r["deck"], r["front"]))
    for gid in sorted(wiki_ids & anki_ids):
        r = records[gid]
        note, cur_deck, orphaned = anki[gid]
        changed = (
            note["Front"] != r["front"]
            or note["Back"] != r["back"]
            or note["Source"] != r["source"]
        )
        if changed:
            plan.update.append((gid, r["page"]))
        if cur_deck != r["deck"]:
            plan.move.append((gid, cur_deck, r["deck"]))
        if orphaned:
            plan.resurrect.append(gid)  # its ULID is back in the vault — un-orphan it
        if not changed and cur_deck == r["deck"] and not orphaned:
            plan.noop.append(gid)
    for gid in sorted(anki_ids - wiki_ids):
        note, _deck, orphaned = anki[gid]
        if not orphaned:  # already-orphaned cards are handled; don't re-flag every run
            plan.suspend.append((gid, note["Source"]))
    return plan, anki


# --- apply -------------------------------------------------------------------
QFMT = "{{Front}}"
# Source is a bare obsidian:// URI; wrap it in a real anchor so it's clickable
# (a bare URL in a field renders as plain text). Self-healed on every run.
AFMT = (
    '{{FrontSide}}<hr id="answer">{{Back}}<br><br>'
    '<a href="{{Source}}">↗ Open in Obsidian</a>'
)


def ensure_notetype(col):
    nt = col.models.by_name(NOTETYPE)
    if nt:
        t = nt["tmpls"][0]
        if (
            t.get("qfmt") != QFMT or t.get("afmt") != AFMT
        ):  # pipeline owns this template
            t["qfmt"], t["afmt"] = QFMT, AFMT
            col.models.update_dict(nt)
        return nt
    mm = col.models
    nt = mm.new(NOTETYPE)
    for f in FIELDS:
        mm.add_field(nt, mm.new_field(f))
    t = mm.new_template("Card 1")
    t["qfmt"], t["afmt"] = QFMT, AFMT
    mm.add_template(nt, t)
    mm.add_dict(nt)
    return mm.by_name(NOTETYPE)


def _set_fields(note, gid, r):
    note["Front"], note["Back"], note["WikiID"], note["Source"] = (
        r["front"],
        r["back"],
        gid,
        r["source"],
    )


def _add_media(col, vault_root, r):
    for m in r["media"]:
        col.media.add_file(
            os.path.join(vault_root, m.asset)
        )  # idempotent (content-hash)


def apply_plan(col, plan, records, anki, vault_root):
    nt = ensure_notetype(col)
    for gid, _deck, _front in plan.add:
        r = records[gid]
        _add_media(col, vault_root, r)
        note = col.new_note(nt)
        _set_fields(note, gid, r)
        note.guid = gid
        note.tags = [MANAGED_TAG]
        col.add_note(note, col.decks.add_normal_deck_with_name(r["deck"]).id)
    for gid, _page in plan.update:
        r, note = records[gid], anki[gid][0]
        _add_media(col, vault_root, r)
        _set_fields(note, gid, r)
        col.update_note(note)
    for gid, _from, to in plan.move:
        note = anki[gid][0]
        col.set_deck(note.card_ids(), col.decks.add_normal_deck_with_name(to).id)
    for gid in plan.resurrect:
        note = anki[gid][0]
        col.sched.unsuspend_cards(note.card_ids())
        col.tags.bulk_remove([note.id], ORPHAN_TAG)
    for gid, _src in plan.suspend:
        note = anki[gid][0]
        col.sched.suspend_cards(note.card_ids())
        col.tags.bulk_add([note.id], ORPHAN_TAG)


def reconcile(
    col, records, vault_root, *, threshold=3, confirm_orphans=False, dry_run=False
):
    plan, anki = compute_plan(col, records)
    if len(plan.suspend) > threshold and not confirm_orphans:
        plan.blocked = True
        return plan  # abort before ANY mutation
    if not dry_run:
        apply_plan(col, plan, records, anki, vault_root)
    return plan


# --- cli ---------------------------------------------------------------------
def _print_plan(plan, dry_run):
    print(
        f"\nplan: {len(plan.add)} add · {len(plan.update)} update · {len(plan.move)} move · "
        f"{len(plan.resurrect)} resurrect · {len(plan.noop)} no-op · {len(plan.suspend)} suspend"
    )
    for gid, deck, front in plan.add:
        print(f"  ADD       {gid[:8]}…  {front[:48]!r} → {deck}")
    for gid, page in plan.update:
        print(f"  UPDATE    {gid[:8]}…  ({page})")
    for gid, a, b in plan.move:
        print(f"  MOVE      {gid[:8]}…  {a} → {b}")
    for gid in plan.resurrect:
        print(f"  RESURRECT {gid[:8]}…  (was orphaned; back in the vault)")
    for gid, src in plan.suspend:
        print(f"  SUSPEND   {gid[:8]}…  source: {src}")
    if plan.blocked:
        print(
            "\nBLOCKED: suspends exceed --orphan-threshold. Re-run with --confirm-orphans "
            "if these deletions are real (likely a parse/scope bug otherwise)."
        )
    elif dry_run:
        print("\n(dry-run — nothing written)")


def _open_collection(path):
    from anki.collection import Collection

    try:
        return Collection(path)
    except Exception as e:  # noqa: BLE001 — best-effort lock detection
        msg = str(e).lower()
        if any(w in msg for w in ("lock", "in use", "busy", "already open")):
            print(
                "collection locked (Anki desktop open on this profile?) — skipping sync."
            )
            sys.exit(0)
        raise


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--collection")
    ap.add_argument("--profile", default="Wiki")
    ap.add_argument("--vault", default=".")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--confirm-orphans", action="store_true")
    ap.add_argument("--orphan-threshold", type=int, default=3)
    a = ap.parse_args(argv[1:])

    vault = a.vault
    # macOS default. Linux: ~/.local/share/Anki2 ; Windows: %APPDATA%/Anki2 —
    # or pass --collection with the full path to your collection.anki2.
    col_path = a.collection or os.path.expanduser(
        f"~/Library/Application Support/Anki2/{a.profile}/collection.anki2"
    )

    # gather + gate pages (only wiki/ can hold cards)
    all_pages = []
    for dp, _d, fs in os.walk(os.path.join(vault, "wiki")):
        for f in fs:
            if f.endswith(".md"):
                all_pages.append(os.path.relpath(os.path.join(dp, f), vault))
    public = card_lib.public_pages(all_pages, cwd=vault)
    errors = []
    for p in all_pages:
        if (
            p not in public
            and card_lib.parse_cards(
                open(os.path.join(vault, p), encoding="utf-8").read(), p
            ).has_section
        ):
            errors.append(
                f"{p}: has a `## Anki Cards` section but is NOT git-public — privacy violation"
            )

    records, rec_errors = build_records(sorted(public), vault)
    errors += rec_errors
    if errors:
        print("ABORT — refusing to reconcile until these are fixed:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        return 2

    if not a.dry_run and not os.path.exists(col_path):
        print(
            f"no collection at {col_path} — open the '{a.profile}' profile in Anki once to create it.",
            file=sys.stderr,
        )
        return 2

    col = _open_collection(col_path)
    try:
        plan = reconcile(
            col,
            records,
            vault,
            threshold=a.orphan_threshold,
            confirm_orphans=a.confirm_orphans,
            dry_run=a.dry_run,
        )
        _print_plan(plan, a.dry_run)
        return 1 if plan.blocked else 0
    finally:
        col.close()


# --- self-test (e2e against a throwaway collection) --------------------------
def _self_test():
    import shutil
    from anki.collection import Collection

    D = "/tmp/anki-reconcile-test"
    shutil.rmtree(D, ignore_errors=True)
    os.makedirs(D)
    ok = True

    def want(name, cond):
        nonlocal ok
        ok = ok and cond
        print(f"  [{'ok' if cond else 'FAIL'}] {name}")

    A = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    B = "01BX5ZZKBKACTAV9WEVGEMMVRZ"
    rec = {
        A: {
            "front": "What is the capital of France?",
            "back": "Paris.",
            "deck": "Wiki::A",
            "source": "obsidian://x",
            "media": [],
            "page": "p.md",
        },
        B: {
            "front": "What is 2 + 2?",
            "back": "Four.",
            "deck": "Wiki::A",
            "source": "obsidian://y",
            "media": [],
            "page": "p.md",
        },
    }
    col = Collection(os.path.join(D, "collection.anki2"))
    try:
        p = reconcile(col, rec, D)
        want("first run adds 2", len(p.add) == 2 and not p.update and not p.suspend)

        p = reconcile(col, rec, D)
        want("second run all no-op", len(p.noop) == 2 and not p.add and not p.update)

        rec[A]["back"] = "Paris, on the Seine."
        p = reconcile(col, rec, D)
        want(
            "edit → 1 update",
            len(p.update) == 1 and p.update[0][0] == A and len(p.noop) == 1,
        )

        rec[B]["deck"] = "Wiki::B"
        p = reconcile(col, rec, D)
        want("folder change → 1 move", len(p.move) == 1 and p.move[0][0] == B)

        del rec[B]
        p = reconcile(col, rec, D)
        want("drop card → 1 suspend", len(p.suspend) == 1 and p.suspend[0][0] == B)
        nid = col.find_notes(f"WikiID:{B}")[0]
        card = col.get_card(col.get_note(nid).card_ids()[0])
        want("orphan actually suspended", card.queue == QUEUE_SUSPENDED)
        want("orphan tagged", ORPHAN_TAG in col.get_note(nid).tags)

        # orphan guard: drop everything, threshold 0 → blocked, no mutation
        p = reconcile(col, {}, D, threshold=0)
        want("orphan guard blocks", p.blocked and len(p.suspend) == 1)
        p2 = reconcile(col, {}, D, threshold=0, confirm_orphans=True)
        want("guard override applies", not p2.blocked)

        want(
            "render_field latex+media",
            render_field("a $x$ ![[assets/public/c.png|20]]")
            == 'a \\(x\\) <img src="c.png" width="20">',
        )
    finally:
        col.close()
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        sys.exit(0 if _self_test() else 1)
    sys.exit(main(sys.argv))
