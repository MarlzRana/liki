#!/usr/bin/env python3
"""Wiki link-graph health check: unresolved links, orphans, dead ends, isolated pages.

Run from the vault root:

    /usr/bin/python3 .agents/skills/lint-wiki/scripts/link_graph.py

Replaces `obsidian orphans/deadends/unresolved`, which cannot be trusted here — it
reports pages as orphans that have real incoming links, and misses real orphans.

Definitions used (they matter when comparing against past lint entries):
  orphan    no incoming [[link]] from any other page under wiki/. index.md is
            deliberately EXCLUDED as a link source: it links to every page by
            design, so counting it would make the check always return zero.
  dead end  no outgoing [[link]] to another wiki page.
  isolated  both of the above — the actionable metric, since a page reachable
            only via the index and leading nowhere is effectively unfindable.
"""

import os
import re
import sys
import collections

WIKI = "wiki"
LINK = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
EMBED = re.compile(r"!\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]")


def load_pages():
    pages = {}
    for root, _dirs, files in os.walk(WIKI):
        for f in files:
            if f.endswith(".md"):
                pages[f[:-3]] = os.path.join(root, f)
    return pages


def main():
    if not os.path.isdir(WIKI):
        sys.exit("error: run this from the vault root (no ./wiki directory here)")

    pages = load_pages()
    out = collections.defaultdict(set)
    inc = collections.defaultdict(set)
    unresolved = collections.defaultdict(list)
    broken_embeds = collections.defaultdict(list)

    scan = dict(pages)
    scan["index.md"] = "index.md"  # checked for unresolved links, not as a link source

    for name, path in scan.items():
        text = open(path, encoding="utf-8").read()

        for target in LINK.findall(text):
            target = target.strip()
            if target.startswith("assets/"):
                continue
            if target not in pages:
                unresolved[target].append(path)
            elif name in pages and target != name:
                out[name].add(target)
                inc[target].add(name)

        for target in EMBED.findall(text):
            target = target.strip()
            if not os.path.exists(target):
                broken_embeds[target].append(path)

    orphans = sorted(n for n in pages if not inc[n])
    deadends = sorted(n for n in pages if not out[n])
    isolated = sorted(set(orphans) & set(deadends))

    print(f"pages: {len(pages)}\n")

    def section(title, items, fmt=lambda x: f"    {x}"):
        print(f"=== {title} ({len(items)}) ===")
        for i in items:
            print(fmt(i))
        if not items:
            print("    (none)")
        print()

    section(
        "UNRESOLVED LINKS",
        sorted(unresolved.items()),
        lambda kv: f"    [[{kv[0]}]]  <- referenced by {', '.join(kv[1])}",
    )
    section(
        "BROKEN EMBEDS",
        sorted(broken_embeds.items()),
        lambda kv: f"    ![[{kv[0]}]]  <- in {', '.join(kv[1])}",
    )
    section(
        "ISOLATED (no incoming, no outgoing)", isolated, lambda n: f"    {pages[n]}"
    )
    section("ORPHANS (no incoming content link)", orphans, lambda n: f"    {pages[n]}")
    section("DEAD ENDS (no outgoing link)", deadends, lambda n: f"    {pages[n]}")

    print(
        f"summary: {len(unresolved)} unresolved, {len(broken_embeds)} broken embeds, "
        f"{len(isolated)} isolated, {len(orphans)} orphans, {len(deadends)} dead ends"
    )


if __name__ == "__main__":
    main()
