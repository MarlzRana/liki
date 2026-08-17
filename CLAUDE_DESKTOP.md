## Users Note System

- The user has a wiki system, where they write journals in an Inbox then a separate AI system organizes the journal entries into existing notes.

### Visualize Tool

Treat **every** visualization as a downloadable artifact — I download all of them through the UI, so the chat host's design system will not be present when I view them. Inline widgets and standalone files are the same case.

- **Output self-contained HTML — never a bare SVG fragment.** Diagrams are drawn in `<svg>`, but always wrapped in a complete `<!DOCTYPE html> … </html>` document with its own palette + font stack, so dark mode and any interactivity survive download. (A raw-SVG download has computed styles flattened and the `@media` block stripped, which silently kills dark mode; the HTML wrapper preserves both.)
- **One diagram per document, split across separate `visualize` invocations.** When a topic has several distinct diagrams, default to a separate call per idea with prose between them — this is almost always the most understandable. Never stuff multiple unrelated diagrams into one artifact. Put more than one `<svg>` in a single document _only_ when the diagrams genuinely integrate — meant to be read side by side as one unit — in which case they share the document's `:root` palette.
- **Make diagrams interactive where it aids understanding.** Default to interactivity when the subject has something to operate — steppers for sequences/lifecycles, sliders for parameters, toggles for state, click-to-reveal for detail. Since these are full HTML documents, the JS ships and works on download. Fall back to static only when there's nothing to manipulate. Wrap any animation in `@media (prefers-reduced-motion: no-preference)`.
- **Never use host theming.** No `c-*` ramp classes, no `t`/`ts`/`th`, no `--color-text-*` or any host-provided variable or font. Define everything myself.
- All colors via CSS custom properties on `:root`, with dark overrides in `@media (prefers-color-scheme: dark) { :root { … } }`. Set `color-scheme` in both. No toggle UI.
- **Every** color routes through a variable — fills, text, strokes, connector lines included. `style="fill:var(--x)"`, never `fill="#…"` or a fixed hex, no exception for "mid-ramp" strokes.
- Dark palette sits on ~`#1e1e1e`, not pure black.

```html
<style>
  :root {
    color-scheme: light;
    --page-bg: #fff;
    --fg: #2c2c2a;
    --muted: #5f5e5a;
    --teal: #dcf1e9;
    --teal-stroke: #0f6e56;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --page-bg: #1e1e1e;
      --fg: #e3e1d9;
      --muted: #a8a69d;
      --teal: #143a30;
      --teal-stroke: #3fae8e;
    }
  }
  html,
  body {
    background: var(--page-bg);
    color: var(--fg);
    margin: 0;
  }
</style>
```
