# Motion and typography

## Durations

The most common mistake is animating UI at camera speed.

| what | duration | why |
|---|---|---|
| an element appearing | **150–300ms** | This is how long real UI takes. Slower reads as sluggish on something that is merely arriving. |
| a state change (press, toggle, select) | 100–200ms | |
| a panel sliding in | 250–350ms | |
| a camera move | ~1s | The camera has mass. This is the one thing that should be slow. |
| a hold on a static frame | 0.6–1.5s | Long enough to read. Do not be afraid of stillness. |

At 60fps: 200ms = 12 frames, 300ms = 18 frames, 1s = 60 frames.

If everything moves at the same speed the cut feels flat. The contrast between
fast UI and a slow camera is what makes it feel designed.

---

## Everything is frame-driven

CSS `@keyframes` **do not advance during a render**. Remotion captures frames
deterministically; a wall-clock animation freezes at its initial state. So
every animation in a vendored component must be re-expressed against
`useCurrentFrame()`.

Standard replacements:

```tsx
// fade-in-up
const p = spring({ frame: frame - at, fps, durationInFrames: 14,
                   config: { damping: 200, stiffness: 120, mass: 0.5 }});
style={{ opacity: p, transform: `translateY(${(1-p)*8}px)` }}

// a blinking caret (1s step)
const on = frame % fps < fps / 2;

// a shimmer/sweep (2.4s loop)
const pos = interpolate(frame % (2.4*fps), [0, 2.4*fps], [100, -100]);
style={{ backgroundPosition: `${pos}% 0`, backgroundClip: "text",
         color: "transparent" }}

// a pulsing glow
const t = (frame % (1.5*fps)) / (1.5*fps);
const pulse = (1 - Math.cos(t * Math.PI * 2)) / 2;
```

Vendor the product's Tailwind config but **drop its `animation` and
`keyframes` blocks** — leaving them in invites a component to silently use one.

---

## Typing

Two separate cadences, and they're different problems.

**Rendered characters**: slice the string by frame. For a hero shot where the
typing carries the whole beat, spread the text across the entire shot rather
than using a realistic rate — otherwise it finishes in a second and you hold
on a static frame for three:

```ts
const chars = interpolate(frame, [typeStart, typeEnd], [0, text.length], { clamp });
return text.slice(0, Math.floor(chars));
```

**Then hold.** After the typing finishes, hold the completed line for
0.5–1.5s. This is when the viewer actually reads it. If you have music, drop
it out here — silence over a finished sentence is a strong beat.

Audible keystrokes are a *separate* rhythm — see `sound.md`. Do not fire one
per character.

---

## Typography for title cards

Type at 1920×1080 needs to be much larger than screen type. Rough scale:

| role | size | weight |
|---|---|---|
| hero word / impact | 200–280px | 700 |
| headline | 78–96px | 600 |
| sub / question | 42–56px | 500–600 |
| caption / label | 24–32px | 500 |

Tracking tightens as size grows: −0.015em at 50px, −0.03em at 80px, −0.045em
at 200px+. Untracked large type looks loose and amateur.

**Animate type with `transform: scale()`, `clip-path` and `opacity` only.**
Never `fontSize`, `letter-spacing` or `width` — those reflow and re-hint the
glyphs mid-animation, which produces a visible shimmer. If a line must change
size, lay it out at the final size and scale it down.

Colour transitions must interpolate RGB, not switch at a threshold.

---

## Hook patterns that work

You have about three seconds. Some shapes that earn them:

**The slam.** A calm setup line is physically knocked out of frame by one huge
word arriving. Give the impact a spring with low damping (`damping: 26,
stiffness: 420`), a 7-frame blur that resolves, a 6-frame camera kick
(+9px, −3px, 0), and a thin accent rule that scales out from the centre. Land
it on a beat. The word should arrive white and take the brand colour *after*
the impact — colour on arrival dilutes the hit.

**The reel.** A slot-machine of real user questions/inputs scrolling past:
one held long enough to read, then a second, then dozens in a motion blur,
decelerating onto the one the video is about. Shows breadth in three seconds
and lands on your story.

Stage it explicitly — hold, step, hold, step, hold, then spin. A single
ease-in-out curve is already moving when the film starts, so the first two
items are never readable. Blur proportional to velocity (`blur = speed * 11`,
capped ~15px) and feather the top and bottom edges so items arrive and leave
rather than being clipped.

**The jolt.** Two states slammed together in the first second — empty vs
complete, blank page vs finished document. The viewer gets the whole value
proposition before reading a word.

**Auto-captions.** The active line is large and white, inactive lines are
smaller and grey; the active one hands off. Familiar from social video, very
legible, works when your hook is two sentences.

Whichever you choose: hold the final state for at least a second before
cutting. A hook that keeps moving until the cut gives the viewer nothing to
land on.

---

## The end slate

Logo, one line, domain. Back to the same background the film opened on so the
cut reads as closed. A very slow scale (1.0 → 1.02 over 2s) keeps it from
being dead. Hold at least 3 seconds — people screenshot end slates.
