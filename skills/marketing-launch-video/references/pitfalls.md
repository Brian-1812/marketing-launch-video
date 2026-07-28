# Pitfalls

Each of these cost real hours on a real build. Read before your first render.

---

## Rendering

**CSS `@keyframes` freeze at frame 0.** Remotion renders deterministically, so
wall-clock animations never advance. Any vendored component using
`animate-fade-in`, a shimmer, a spinner or a blink will render static. Vendor
the Tailwind config *without* its `animation`/`keyframes` blocks so nothing
can silently use one, and re-express every animation against
`useCurrentFrame()`. See `motion.md`.

**`delayRender()` at module scope fails the render.** It runs during bundle
evaluation, before there is a render scope. It works for stills and then blows
up on `render` with a stack pointing at the import. Put it in a hook:

```tsx
function useFontsReady() {
  const [handle] = React.useState(() => delayRender("fonts"));
  React.useEffect(() => {
    let cancelled = false;
    document.fonts.ready.then(() => { if (!cancelled) continueRender(handle); });
    return () => { cancelled = true; };
  }, [handle]);
}
```

Without it the opening frames render in the fallback face and the weight
visibly swaps mid-shot.

**Remotion bundles with webpack, not Vite.** Path aliases from `vite.config.ts`
are not read. Re-declare them in `remotion.config.ts` via
`Config.overrideWebpackConfig()`.

**Pin React to match the product.** Importing components built against React
18 into a project running React 19 gives duplicate-React hook errors. Same for
Tailwind — v3 and v4 have different configs and different Remotion plugins
(`@remotion/tailwind` vs `@remotion/tailwind-v4`).

**Bring the theme CSS.** If the product's colours are CSS custom properties
(`hsl(var(--primary))`), vendoring the Tailwind config alone renders every
component colourless. You need the `:root` block too.

**Cap concurrency.** Remotion spawns a Chrome tab per slot. On 16GB, use
`--concurrency=4`; the default (core count) swaps and gets slower.

**Add a silent composition.** `defaultProps: { withAudio: false }` so stills
render before the audio file exists.

---

## Framing

**Measure before you scroll.** A document that fits its pane needs no
scrolling — applying a scroll anyway pushes it clean off and renders a *blank
frame*. Render a still, work out the actual content height, then decide
between scrolling the content and panning the camera.

**Don't centre a message list.** Vertically centring a short conversation to
make framing easier looks broken — real chat renders from the top. Fix the
camera instead. (Bottom-anchoring *is* right in a narrow column where the
latest turn should sit above the composer.)

**Clear the input after send.** An easy one to miss: if the composer keeps its
text for the rest of the video, every subsequent shot has a stale question
sitting in it.

**Respect the product's element order.** If a generated file appears above the
action toolbar in the real UI, it must here. A window where the toolbar is on
screen with nothing under it reads as a missing element — and someone who
knows the product will spot it immediately.

**Cuts need content.** Landing a cut on a frame that's still waiting for its
first element reads as a stall. Start the element's fade *before* the cut.

**Clipping paths clip their children.** A reveal mask on a text block also
clips a rule positioned below it. Move decorations outside the masked element.

**`AbsoluteFill` is a column flexbox.** `items-*` is horizontal, `justify-*` is
vertical. Swapping them puts your bottom caption in the middle of the frame.

---

## Content

**Never invent domain facts.** In any specialised domain — legal, medical,
financial, scientific — one invented detail costs you every expert in the
audience. Pull the real thing from the repo, the corpus, the API or the docs,
and keep a provenance note. Names, dates and amounts are fine to invent;
claims about the world are not.

**Don't reproduce the product's bugs.** If the generator you're demoing has a
rendering defect (repeated section numbers, an empty cell, a wrong label),
render it *correctly* in the video and tell the user about the bug. The video
should show the product at its best; the bug report is a separate, valuable
deliverable.

**Excerpting changes numbering.** If you show 7 of 12 clauses, renumber them
1–7. Gaps read as a rendering bug rather than an edit.

---

## Process

**Look at the stills.** Render one per shot and actually open the PNG. Almost
every framing problem is invisible in code and obvious in a still.

**Tune numerically.** Easing curves, scroll distances, spectra — all
computable. A 20-line Python script that prints where a bezier puts you at
each frame is faster and more reliable than rendering and squinting. Do this
before rendering, not after.

**Keep every beat in one table.** One exported object of absolute frame
numbers, read by the DOM, the camera and the sound script. Retiming then means
editing one block. Beats scattered through components make retiming a
multi-hour hunt.

**Put shot boundaries on a musical beat.** Even with no music. It gives the
cut rhythm and means a bed can be added later without re-editing.

**Say what you couldn't check.** You can read stills; you cannot judge how
eight seconds *feels* and you cannot hear audio. State that plainly rather
than implying you verified it.
