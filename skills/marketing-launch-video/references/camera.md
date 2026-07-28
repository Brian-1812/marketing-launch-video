# The camera

The single most useful idea here: **separate layout space from frame space.**

Lay the product out at a fixed size — 1920×1080 — regardless of the output
resolution. The "camera" is then a transform on that layout: a focus point
plus a scale. This is what makes shots tunable, because a shot becomes two
coordinates you can read straight off a still.

```ts
interface Shot { cx: number; cy: number; scale: number }
```

`cx, cy` is the point in layout space you want centred. Copy it from a
rendered still: see what you want in the middle, note its pixel position,
put those numbers in. No trial and error on translate values.

Copy `assets/useCamera.ts` into `src/hooks/`. It handles the interpolation,
the clamping and hard cuts.

---

## Clamping

Always clamp the translate so the scaled layout covers the frame. A shot near
an edge should slide back in rather than expose blank canvas:

```ts
tx = clamp(frameW/2 - cx*scale, frameW - LAYOUT_W*scale, 0)
```

The consequence worth knowing: an element at the bottom of the page can never
be vertically centred in a close-up, because centring it would require showing
space below the page. This is correct behaviour, and it's also the reason for
the isolation trick below.

---

## Cut, push, morph — and when each is right

**Push-in** (spring, ~1s, heavily damped): "look closer at the same thing."
Use `spring({ config: { damping: 200, stiffness: 60 } })`. Never linear — a
linear camera move is the fastest way to make a video feel cheap.

**Hard cut** (instant): "we are somewhere else now." Reframing onto a
different surface wants this. A cut is punchier than a push and costs no time,
which matters when you have 45 seconds.

Land a cut on a frame where something is already happening. Cutting to a
frame that's still waiting for content reads as a stall — if a message is
about to appear, start its fade *before* the cut so it's already there.

**Morph**: two elements that share a position and shape transform into each
other. This is the most expensive-looking transition and it's usually cheap to
build, because products are full of elements that occupy the same slot:

- A composer growing into a form that replaces it — animate the container's
  *height* with `overflow: hidden`, not `scaleY`. Scaling distorts the type.
- A card opening into the thing it represents — the destination scales up
  from ~0.9 with opacity as the cut lands, so the cut reads as the card
  expanding rather than as an unrelated screen.

**Pan**: content moving under a fixed camera (a scroll), or the camera
translating across a large surface. Good for showing that something is long —
a document, a list, a log.

---

## Isolate the component instead of cropping the page

This is the trick that fixes the most framing problems.

When a shot is about one component — the input, the generated document, a
card — do not crop into the page to reach it. Two things go wrong: the
component sits at the page edge with a screenful of dead background beside it,
and at any scale large enough to read, a wide component overflows the frame.

Instead render that component **on its own**, at its true width, uniformly
scaled, centred in the frame:

```tsx
<AbsoluteFill className="items-center justify-center bg-background">
  <div style={{ width: 768, transform: `scale(1.92)` }}>
    <Composer {...} bare />
  </div>
</AbsoluteFill>
```

Keep the component at its real layout width and scale the whole thing. Every
radius, border and shadow stays in the product's proportions — which is what
re-laying it out at 1450px would destroy.

Give such components a `bare` prop that drops page chrome (side padding,
gradient scrims, sticky positioning) that only makes sense in situ.

**The exception where cropping is right**: when the component's own bounds
should become the frame's bounds. If a document pane is 1019px wide, a camera
at `scale = 1920/1019 = 1.88` puts the pane's edges exactly on the frame's
edges. That reads as a deliberate reframe rather than a zoom — and it's what
someone means when they say "cut to fit the document".

---

## Practical scale ranges

At 1920×1080, with the product laid out at that size:

| shot | scale | for |
|---|---|---|
| establishing | 1.0 | the whole app. Use it twice, briefly. It is not a default. |
| working | 1.3–1.6 | a column of content plus context |
| reading | 1.6–2.0 | text you want the viewer to actually read |
| detail | 2.0–2.6 | a single control, a changed word, a button press |

Below 1.3 the type is too small to read on a phone, which is where most of
these videos are watched. Above 2.6 you're usually better off isolating.

**Content must exist where the camera looks.** A tight shot on a chat thread
that currently holds one message frames mostly empty page. Either start the
next element earlier so the frame has something in it, or open wider and push
in as content arrives.

---

## Vertical

A 1080×1920 crop of a 1920×1080 layout does not work. To cover a vertical
frame the scale can never go below 1.78, which leaves ~607px of visible layout
— narrower than a typical content column, so text clips on both sides at every
shot.

Two options that do work:

1. **A 1080×1080 window** inside the vertical frame, with caption bands above
   and below. Minimum scale drops to 1.0 and every shot becomes possible.
2. **A genuine mobile layout** — rebuild the product's responsive/mobile
   view, which is already narrow. More work, better result.

Don't promise a vertical cut as a trivial re-render. It isn't.
