#!/usr/bin/env python3
"""Backfill `<!-- anki: MINT -->` placeholders with real, unique ULIDs.

Phase 2 (generation) writes each card block with a `MINT` placeholder; this
deterministic step replaces every placeholder with a fresh ULID, collision-checked
against every existing card ID anywhere in the vault. An LLM can't be trusted to
mint unique, sortable ids — so it never does; this does.

Stdlib only. Idempotent: a ULID is never touched, only `MINT`.

    /usr/bin/python3 .agents/skills/process-inbox/scripts/mint_ids.py <page.md> ...
    /usr/bin/python3 .agents/skills/process-inbox/scripts/mint_ids.py --self-test
"""

from __future__ import annotations

import os
import re
import sys
import time

# Crockford base32 (no I, L, O, U) — matches card_lib.ULID_RE
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ULID = re.compile(r"<!--\s*anki:\s*([0-9A-HJKMNP-TV-Z]{26})\s*-->")
_MINT = re.compile(r"<!--\s*anki:\s*MINT\s*-->")
_SCAN_ROOTS = ("wiki", "inbox")  # where existing ids might live


def new_ulid(now_ms=None, rand=None):
    """A canonical ULID: 48-bit ms timestamp + 80-bit randomness → 26 Crockford chars."""
    ts = (time.time_ns() // 1_000_000 if now_ms is None else now_ms) & ((1 << 48) - 1)
    r = int.from_bytes(os.urandom(10), "big") if rand is None else rand
    val = (ts << 80) | (r & ((1 << 80) - 1))
    out = []
    for _ in range(26):
        out.append(_CROCKFORD[val & 31])
        val >>= 5
    return "".join(reversed(out))


def existing_ulids(roots=_SCAN_ROOTS):
    """Every card ULID already present anywhere in the vault (for collision-checking)."""
    seen = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if not f.endswith(".md"):
                    continue
                try:
                    text = open(os.path.join(dirpath, f), encoding="utf-8").read()
                except OSError:
                    continue
                seen.update(_ULID.findall(text))
    return seen


def mint_in_text(text, taken, gen=new_ulid):
    """Replace every MINT placeholder with a fresh ULID not in `taken` (mutated).

    Returns (new_text, [minted_ids]). Pure except for growing `taken`."""
    minted = []

    def repl(m):
        while True:
            u = gen()
            if u not in taken:
                taken.add(u)
                minted.append(u)
                return m.group(0).replace("MINT", u)

    return _MINT.sub(repl, text), minted


def main(argv):
    pages = argv[1:]
    if not pages:
        print(
            "usage: mint_ids.py <page.md> ...  (the pages generation touched)",
            file=sys.stderr,
        )
        return 2
    taken = existing_ulids()
    total = 0
    for p in pages:
        try:
            text = open(p, encoding="utf-8").read()
        except OSError as e:
            print(f"skip {p}: {e}", file=sys.stderr)
            continue
        new, minted = mint_in_text(text, taken)
        if minted:
            # Atomic write: a crash / disk-full mid-write must not truncate the
            # user's note. Write a sibling temp file, then rename over the original.
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(new)
            os.replace(tmp, p)
            total += len(minted)
            print(f"{p}: minted {len(minted)}")
    print(f"minted {total} id(s) across {len(pages)} page(s)")
    return 0


# --- self-test ---------------------------------------------------------------
def _self_test():
    ok = True

    def want(name, cond):
        nonlocal ok
        ok = ok and cond
        print(f"  [{'ok' if cond else 'FAIL'}] {name}")

    print("new_ulid:")
    u = new_ulid()
    want("26 chars", len(u) == 26)
    want("crockford alphabet", all(c in _CROCKFORD for c in u))
    want("matches card ULID regex", bool(re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", u)))
    # time-sortable: an earlier timestamp encodes lexicographically smaller
    a = new_ulid(now_ms=1000, rand=0)
    b = new_ulid(now_ms=2000, rand=0)
    want("time-sortable", a < b)
    want("uniqueness (10k)", len({new_ulid() for _ in range(10000)}) == 10000)

    print("mint_in_text:")
    sample = (
        "> [!card]- Q1\n> A1\n> <!-- anki: MINT -->\n\n"
        "> [!card]- Q2\n> A2\n> <!-- anki: 01ARZ3NDEKTSV4RRFFQ69G5FAV -->\n\n"
        "> [!card]- Q3\n> A3\n> <!-- anki: MINT -->\n"
    )
    taken = {"01ARZ3NDEKTSV4RRFFQ69G5FAV"}
    new, minted = mint_in_text(sample, taken)
    want("minted exactly 2", len(minted) == 2)
    want("no MINT left", "MINT" not in new)
    want("existing id untouched", "01ARZ3NDEKTSV4RRFFQ69G5FAV" in new)
    want(
        "minted ids are ULIDs",
        all(re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", m) for m in minted),
    )
    want("no collision with existing", "01ARZ3NDEKTSV4RRFFQ69G5FAV" not in minted)
    # idempotent: second pass mints nothing
    _, again = mint_in_text(new, taken)
    want("idempotent (0 on re-run)", len(again) == 0)

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        sys.exit(0 if _self_test() else 1)
    sys.exit(main(sys.argv))
