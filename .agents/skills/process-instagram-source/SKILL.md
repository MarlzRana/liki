---
name: process-instagram-source
description: Extract the content of an Instagram image or carousel post so it can be written into the wiki. Use when an inbox note contains an instagram.com/p/ link (often with an "@Agent transcribe this" directive), or when the user asks to pull the text out of an Instagram post. Covers public and private posts. Does not cover reels or video.
---

# Process an Instagram Image Post

Instagram posts arrive in `inbox/` as a bare URL plus an `@Agent transcribe this` directive. The content is in the **images**, not the caption — so "transcribe" means reading the slides, not copying the caption.

**Scope:** image posts and carousels (`instagram.com/p/<shortcode>/`). Reels and video are out of scope.

## Prerequisites

Chrome DevTools MCP configured in `.mcp.json` with `--autoConnect`, plus remote debugging enabled once at `chrome://inspect/#remote-debugging`. Requires Chrome 144+.

`--autoConnect` attaches to your **real, logged-in Chrome profile**. Two consequences:

- Private and followers-only posts become readable, because you're already authenticated.
- The agent can see everything in that profile — all tabs, cookies, session and local storage. Stay on `instagram.com` for the duration of this skill and don't browse anything else.

Always work in a **new tab** (`new_page`) and close it when done. Never take over the user's selected tab.

## Step 1 — Open the post and get the caption

```
new_page → https://www.instagram.com/p/<shortcode>/
```

Then read the page text in one call:

```js
() => {
  const t = document.body.innerText || "";
  return {
    wall: /Log In\nSign Up/.test(t),
    text: t.slice(0, 4000)
  };
}
```

This returns the caption, the comments, and the author handle. Public posts return full caption text **even when a login wall is showing** — a visible "Log In / Sign Up" does not mean extraction failed. Check whether you actually got caption text before assuming you need auth.

If the text is only chrome (`Log In`, `Sign Up`, language list, footer) with no caption, the post is private or restricted — see *Private posts* below.

**Judge the caption before trusting it.** Some accounts put the whole substance in the caption; others put a bare "Follow @x for more content like this" and hold everything in the slides. Both shapes have appeared. If the caption is a follow prompt, the slides are the only source.

## Step 2 — Force-load the carousel

Instagram lazy-loads carousel slides: **only about two are in the DOM initially**, regardless of how many the post has. Clicking through programmatically loads the rest. Harvest into a `Map` keyed by `src` so re-renders don't produce duplicates.

Filter on the alt-text prefix Instagram generates — `Photo by <Author> on <Date>` — to pick out slides and exclude avatars, comment thumbnails, and the "more posts" grid.

```js
async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const seen = new Map();
  const AUTHOR = "First Principles Consultants on July 21";  // set per post
  const harvest = () => {
    document.querySelectorAll('img').forEach(i => {
      const a = i.alt || '';
      if (a.includes(AUTHOR)) seen.set(i.src, a);
    });
  };
  harvest();
  for (let k = 0; k < 12; k++) {
    const next = [...document.querySelectorAll('button')]
      .find(b => (b.getAttribute('aria-label') || '') === 'Next');
    if (!next) break;
    next.click();
    await sleep(700);
    harvest();
  }
  return { count: seen.size, slides: [...seen.entries()].map(([src, alt], i) => ({ n: i + 1, alt, src })) };
}
```

Loop a couple more times than the dot count so the last slide is definitely reached. Keep the `src` values — step 3 needs them.

## Step 3 — Read the slides

**Instagram auto-OCRs images into their alt text.** For text-heavy slides this is often the entire content, for free, with no screenshots. The format is:

> `Photo by X on DATE. May be a graphic of poster and text that says '<the OCR>'.`

Take the text after `that says` and clean it. Expect garbling on stylised or overlapping type — background decoration OCRs into noise while the foreground body text usually comes through cleanly. Keep the clean parts, discard the noise.

**When alt text carries no quoted content** — e.g. `May be a Twitter screenshot of text.` or `May be a doodle of poster, crossword puzzle and text.` with nothing after it — the OCR failed and you must look at the image.

To look at a slide, **navigate to its raw CDN `src` and take a full-page screenshot**:

```
navigate_page → <the slide's src>
take_screenshot → format: webp, quality: 92, fullPage: true
```

Do **not** screenshot the post page for this. Instagram throws a "Never miss a post from…" signup modal over the viewport that obscures exactly the content you want, and the page screenshot also drags in Instagram's UI chrome. Navigating straight to the image URL sidesteps the modal entirely and gives a clean, readable render.

Only fetch the slides whose alt text was empty. Slides with good OCR need no screenshot.

## Step 4 — Close the tab

`close_page` on the tab you opened. Leave the user's browser as you found it.

## Private posts

With `--autoConnect` the session is already authenticated, so steps 1–3 work unchanged. If a post still won't load:

- Confirm remote debugging is on at `chrome://inspect/#remote-debugging`.
- Confirm the logged-in account actually follows the author.
- `list_pages` to confirm you attached to the real Chrome rather than a sandboxed instance — an isolated instance has no session.

## Do not use yt-dlp for image posts

Tested and ruled out. yt-dlp authenticates and resolves the post fine, then fails with **`No video formats found!`** on both a single-image post and a ten-slide carousel. It is a video downloader; an image post has nothing it will download.

The error pair is still a useful auth diagnostic if you ever reach for yt-dlp on a reel:

| Error | Meaning |
|---|---|
| `Instagram sent an empty media response` | Cookies are not working |
| `No video formats found!` | Cookies work; the post genuinely has no video |

If you do need cookies for something, export once and reuse the file — `--cookies-from-browser chrome` read a stale snapshot in testing, because Chrome writes its cookie DB lazily:

```bash
yt-dlp --cookies-from-browser chrome --cookies ./cj.txt --skip-download --print id <url>
```

**That file contains a live `sessionid`.** Write it to `/tmp`, never into the vault, and delete it as soon as you're done.

## Writing the result into the wiki

Follow `process-inbox` for routing, frontmatter, and archiving. Three things specific to Instagram sources:

**Transcribe; don't embed.** Instagram captures are usually text overlaid on an unrelated photo, and screenshots of the app carry Instagram's UI plus, often, a bystander in frame. Embedding those publishes a third party's likeness for no informational gain once the text is transcribed. Transcribe the text and leave the capture out.

The exception is an image that **is** the information — a diagram, chart, or pipeline figure. Embed that, and if the note lands in `wiki/Technical/`, promote it to `assets/public/` per the `<assets>` rules in AGENTS.md.

**Attribute the account.** Close the page with a source line naming the handle:

```markdown
> Source: [@handle](https://www.instagram.com/handle/) on Instagram
```

**Add a caveat when the post oversells.** These posts often carry unverifiable quantitative claims ("output quality 6.2/10 → 9.1/10") or breathless framing ("engineers leaked a technique"). Transcribe the substance faithfully, then note plainly that the figures are self-reported with no methodology. The owner is an ML engineer and wants the claim and its credibility separated, not smoothed over.

## Worked example

`inbox/Socratic Prompting.md` held one URL and `@Agent transcribe this`. The caption was a bare follow prompt. The carousel had 10 slides; 2 were in the DOM. Force-loading yielded all of them, 8 with usable OCR. Slides 3 and 7 had empty alt text and were read from their CDN URLs — slide 7 turned out to hold the three-part prompt structure, the only genuinely reusable part of the post. Total: 2 screenshots instead of 10.
