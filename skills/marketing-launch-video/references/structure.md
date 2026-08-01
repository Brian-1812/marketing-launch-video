# Structure — one story, or chapters?

There are two shapes that work. Picking the wrong one costs you the whole
build, so decide before you write a line of the timeline.

---

## Shape A — the single narrative (default)

**One user doing one job and getting one artifact.**

```
hook → ask → the product works → the artifact → the user changes it → slate
```

A person wants something, asks for it, watches the product do something hard,
gets a concrete thing, and stays in charge of it. No labels, no chapters, no
narration. The viewer infers the features from watching them happen.

**Use it when** you can get inside the product, and when its capabilities occur
*in sequence within one session*. Research → draft → edit is not three
features; it's one workflow. Chaptering a natural sequence into three labelled
acts fights the material — you re-establish context three times and lose the
through-line that makes anyone care.

This is the stronger film when it applies. It has emotional continuity: the
viewer follows a person, not a feature list.

---

## Shape B — the chaptered feature film

**Three features, each introduced by a plain-language label, then shown.**

```
hook → [label 1 → feature 1] → [label 2 → feature 2] → [label 3 → feature 3] → slate
```

**Use it when:**

- **The product is gated** and you're building from its landing page. You have
  feature cards and marketing copy but no session to follow — there is no one
  story available, so don't fake one. See `discovery.md`.
- **The features genuinely don't share a user journey.** Different people, at
  different times, for different reasons. A billing tool's "invoicing",
  "expenses" and "reporting" are used by three different roles.
- **The deliverable is really several deliverables.** Chapters give you clean
  cut points, so one build yields the full film *plus* three standalone
  10–15s feature clips for individual posts. That is often the real reason to
  choose this shape, and it's a good one.

**What it costs:** three cards at ~2s each plus transitions is 15–20% of a
45-second runtime spent on words rather than product. Budget for it — either
accept a shorter demo per feature, or make the film 60s.

---

## The middle path — overlay labels on a single narrative

Often the best answer. Keep Shape A's continuous story, but name each
capability *over* the action at the moment it becomes visible: a lower-third
or corner label as the sources panel slides in, as the document fills the
frame, as the tracked changes land.

You get the legibility of chapters and the clip boundaries, at close to zero
runtime cost, and the story never fragments. This is how long-form Apple
product films handle it — the narrative runs and a word appears over it.

Offer this when someone asks for chapters on a product whose features are
sequential. It usually wins, and building both from the same project is
cheap because the shot boundaries already exist.

---

## Designing the chapter card

A chapter card is not a title card. It is a held frame with two lines,
and its job is to be read and then get out of the way.

```
┌──────────────────────────────────────────┐
│                                          │
│   01 ─────                               │   index + rule, accent colour,
│                                          │   24-28px, mono or tracked caps
│   Instant legal research                 │   HEADING  72-88px, weight 600
│                                          │
│   Every answer links to the article of   │   SUMMARY  34-40px, weight 400
│   law it came from, on the official       │   muted colour, max 2 lines
│   registry.                              │
│                                          │
└──────────────────────────────────────────┘
```

**Timing.** 2.0–2.5s total: heading in over 12 frames, summary 8 frames later,
hold ~1.2s, then leave. Under 2s and nobody finishes the summary; over 3s and
the film stalls.

**Layout.** Left-aligned at roughly the same x as the product content that
follows, on the film's dark background. Centred cards read as interstitials
from a slide deck. The number (`01`, `02`, `03`) is worth including — it tells
the viewer how much is left, which measurably keeps people watching.

**Motion.** Type in with `clip-path` + `opacity` only, never `fontSize` or
`letter-spacing` (they reflow and re-hint the glyphs mid-shot). A slow 1.0 →
1.02 scale over the hold keeps it from being dead.

**Card and content must share the background** so the transition into the
feature can be a push rather than a cut — see below.

---

## Writing the labels

This is copywriting, and it's where most chaptered videos fail. The heading is
a *claim about the outcome*; the summary is *how*.

Rules:

**Name the outcome, not the mechanism.** "Instant legal research" beats
"RAG-powered retrieval over 40,000 documents". Nobody buys the mechanism.

**Heading: 2–5 words.** It has to be readable in a glance at thumbnail size.
If it needs a comma it's too long.

**Summary: one sentence, under 14 words.** It earns the heading. Prefer a
concrete noun over a category — "links to the article of law" beats "verifiable
sources".

**Steal the product's own words.** The landing page already contains copy the
company approved, in their voice, with their positioning. Use it. Trim it,
don't rewrite it — if you invent new claims you may be promising something the
product doesn't do.

**Do not make a claim the animation doesn't then show.** If the label says
"in seconds", the animation has to resolve in seconds. A label that overpromises
against its own footage is worse than no label.

| ✗ | ✓ |
|---|---|
| "Powerful AI-driven document generation" | "Drafts the contract" |
| "Seamlessly integrated editing workflow" | "Change it by asking" |
| "Advanced multi-source verification engine" | "Every claim, sourced" |

Write them in the product's language first if the film isn't in English —
translating a good English label usually produces a worse one.

---

## Transitions between chapters

The transition is what stops this feeling like a slideshow. Pick one and use
it every time — inconsistent transitions read as indecision.

**Push through (best default).** The chapter card slides up and out as the
product screen rises into its place, both moving together over ~20 frames on a
single eased curve. Reads as turning a page.

**Match cut.** End the previous feature framed on some element, and open the
next card with a shape in the same position and size. Expensive to choreograph,
excellent when it lands.

**Dip to background.** The simplest: the feature fades to the film's base
colour over 10 frames, the card fades up out of it. Always acceptable, never
exciting. Use it when the two screens have nothing in common.

Whichever you pick: **one whoosh per chapter transition, and nothing else.**
The shot is moving, so it takes a whoosh, not a swish — and the arc's peak must
land on the cut frame, so start it ~350ms early (see `sound.md`).

In the music spec, put a section boundary on each chapter card frame. Strip
back to `pad` under the card and bring the layers in as the feature starts —
the arrangement then does the pacing work for you (see `music.md`).

---

## Ordering the chapters

Not arbitrary. Order by **how quickly the value is legible**, not by how the
product's nav is ordered or how impressive the engineering is.

1. **First: the thing that is obviously useful in three seconds.** You are
   still earning attention.
2. **Second: the thing that is hardest to believe.** Now that they trust you,
   spend the credit on the capability that makes people say "wait, it does
   that?"
3. **Third: the thing that makes it safe to adopt.** Control, editing,
   review, export, undo. Ending on "and you stay in charge" is what converts
   interest into a signup.

Three is the number. Two feels thin, four means each gets under ten seconds
and none of them land. If the product has six features, the other three go in
the description, not the film.
