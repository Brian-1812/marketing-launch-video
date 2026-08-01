---
name: marketing-launch-video
description: Produce a professional, animated launch or marketing video for a software, SaaS or AI product — given only a product URL, or a local dev server, or an existing repo. Rebuilds the product UI in Remotion as frame-driven React (rather than screen-recording it), then choreographs camera, typography, sound effects and a music bed into a 30–60s cut. Works even when the product is behind a login, by building a chaptered feature film from the landing page's own feature cards and components. Use this skill whenever someone asks for a launch video, product demo video, promo video, marketing video, product trailer, teaser, "a video for our landing page", "something to post on X/LinkedIn for launch", "an Apple-style / YC-style product demo", or wants to animate their app for marketing — even if they only paste a URL and say "make a video for this". Also use it when someone wants to improve, retime, re-score, add background music or sound to a product video they already have, or asks for a specific musical feel (energetic, calm, cinematic, minimal, warm, tense).
---

# Launch video for a software product

Produce a 30–60 second video that makes someone understand and want the product.

## The decision that shapes everything: rebuild, don't record

Screen recordings fight you. Real latency is dead air. Retakes are expensive.
You can't hold a frame, you can't slow one beat and speed another, and you
can't crop tightly without hitting compression mush.

So rebuild the UI as frame-driven React inside Remotion. Every visual is a
pure function of `useCurrentFrame()`. Typing lands on an exact curve, a
loading state resolves on the beat, and a retake costs one number.

This is only reasonable because you can read the product's actual code (if
local) or DOM+CSS (if hosted) and reproduce it faithfully. Do that — take the
real class names, the real colours, the real copy. The rebuild should be
indistinguishable from a recording, then better.

**When to record instead:** heavy 3D, video content inside the product, a
canvas/WebGL surface, or a native desktop app. If a specific surface can't be
rebuilt, record just that surface and composite it with `<OffthreadVideo>`.

---

## Phase 1 — Understand the product

Read `references/discovery.md` before starting this phase. It covers the
browse-and-triage procedure, the credentials conversation, and how to extract
a design system from a live site.

Short version:

- **Given a URL**: browse it. Landing page first (it tells you how they
  position themselves), then the app itself. Work out what job the product
  does for whom.
- **Given a local repo/dev server**: read the code. Far richer — you get the
  real components, the real theme tokens, the real seed data.
- **Triage the pages.** Most products have 20 screens and 3 that matter. Auth,
  settings, billing, privacy, account, onboarding boilerplate — these are
  almost never the story. Find the screen where the product does the thing
  only it can do.
- **If the good stuff is behind a login**, ask first — test credentials, or a
  seeded account in their local dev. If neither is available, don't give up
  and don't fake a session you never saw: switch to the chaptered shape and
  build from the landing page's own feature cards, copy and components.
  `discovery.md` has the harvest procedure and the honesty rules.

Then confirm your read with the user before building — a wrong read of the
product costs an entire build. Show them: what you think the product does, the
2–4 screens you plan to feature, the hero scenario, the shot list, and the
music question (see Phase 4). One checkpoint, then run.

---

## Phase 2 — Pick the shape

Read `references/structure.md`. Two shapes work; choosing wrong costs the
build.

**Shape A — the single narrative. The default.** One user doing one job and
getting one artifact. Not a feature tour.

| beat | job |
|---|---|
| **Hook** (0–5s) | State the problem in the viewer's own words. No UI yet. |
| **Ask** (5–12s) | The user asks for the thing. Tight on the input. |
| **Work** (12–25s) | The product visibly does something hard. Show the receipts. |
| **Artifact** (25–35s) | The output, in full, at readable size. |
| **Control** (35–45s) | The user changes it and stays in charge. |
| **Slate** (45–50s) | Logo, one line, domain. |

The **Work** and **Control** beats are what separate a real demo from a
mockup. "It asked me instead of guessing" and "I could edit what it made" are
trust arguments, and trust is what a launch video is actually selling.

Pick the moment where the product does something a person couldn't easily do
themselves, and make the output concrete and visible — a generated document, a
built chart, a fixed bug, a deployed site. Concrete artifacts are what people
remember.

**Shape B — the chaptered feature film.** Three features, each introduced by a
plain-language label card, then shown.

```
hook → [01 label → feature] → [02 label → feature] → [03 label → feature] → slate
```

Use it when the product is **gated** and you're working from its landing page,
or when the features genuinely don't share a user journey, or when you want
three standalone clips out of one build. Three is the number — four means none
of them land.

**Don't chapter a sequence.** If the capabilities happen one after another in
a single session (research → draft → edit), that's one workflow, and labelling
it as three features fights the material. If someone asks for chapters on a
sequential product, offer the middle path instead: keep the single narrative
and put the labels *over* the action as each capability appears. Same
legibility, same clip boundaries, no runtime cost, story intact.

`structure.md` covers chapter-card design, how to write the labels (name the
outcome, not the mechanism; steal the product's own words), transitions, and
ordering.

---

## Phase 3 — Ground everything

Whatever domain the product is in, **do not invent its content**. If it's a
legal product, the statute must be real. If it's analytics, the numbers must
be plausible and internally consistent. If it's a code tool, the code must
compile in the reader's head.

Pull the real thing out of the repo, the API, the seed data, or the docs.
Domain experts watch these videos and one invented detail costs you all of
them. Party names, dates and dollar figures are fine to invent — those are
specific to a customer, not claims about the world.

Keep a provenance note in the data file saying where each fact came from.
Future-you will want it.

---

## Phase 4 — Build

Run the scaffold, which pins the versions that actually work together and
writes the config:

```bash
python3 <skill-dir>/scripts/scaffold_video.py <target-dir> \
    --name "product-launch" --fps 60 --seconds 45
```

It creates a standalone Remotion project (its own git repo — never add video
tooling to the product's repo unless asked), copies in `useCamera.ts`, and
leaves you a timeline module to fill in.

Then, in order:

1. **`src/timeline.ts`** — frame math and shot boundaries. Pick a BPM whose
   beat is a whole number of frames (at 60fps: 120 BPM = 30 frames, 90 BPM =
   40). Put every shot boundary on a beat. Even with no music, this gives the
   cut an internal rhythm, and it means a music bed can be added later without
   re-editing.

2. **`src/data/script.<lang>.ts`** — every string, every number, every piece
   of document content, in one file with provenance comments. Nothing
   hard-coded in components. Retiming and translating both become trivial.

3. **Components** — recreate the product's UI. Copy real class names. If the
   product uses Tailwind, vendor its config and theme CSS; if it uses CSS
   variables for colour, you must bring those over or everything renders
   colourless.

4. **`src/scenes/ProductScene.tsx`** — one exported `B` object holding every
   beat as an absolute frame number. Everything reads from it: the DOM, the
   camera, the sound. Retiming means editing that block and nothing else.

Read `references/camera.md` for the shot system, `references/motion.md` for
durations and typography.

---

## Phase 5 — Audio

Two tracks, two files, two `<Audio>` tags: **effects** and **music**. Keep
them separate so either can be replaced without regenerating the other.

**Effects** — `references/sound.md`. Restraint is the whole discipline: a
45-second video usually needs three to five events total. A pop means a thing
appeared, a swish means an element moved inside the shot, a whoosh means the
*shot* moved.

```bash
python3 <skill-dir>/scripts/make_sfx.py sfx.spec.json public/sfx.wav
```

**Music** — `references/music.md`. **Ask before you build one.** Most people
have an opinion and many already have a track; asking costs a sentence and may
save the entire effort:

> Do you want a music bed? If you have a track, send it and I'll cut to it. If
> not I can synthesize one — energetic, calm, cinematic, minimal, warm, or
> tense?

If they have a track, cut to it: find its BPM, set the timeline to match, move
the shot boundaries onto its bars. Otherwise synthesize a bed whose
arrangement changes land on your cuts to the frame:

```bash
python3 <skill-dir>/scripts/make_music.py music.spec.json public/music.wav
```

Put a `sections` entry on each real shot boundary, one `hits` entry on your
biggest cut, and a `ducks` entry under any held line you want read rather than
felt. Music at peak ~0.30, effects at ~0.62. Choose the mood from what the
product *is* — serious subject matter takes a calmer bed, and a busy cut needs
a sparser one.

---

## Phase 6 — Verify with stills, before you render

This is the tight loop, and skipping it wastes hours.

```bash
npx remotion still <CompositionId> out/f0700.png --frame=700
```

Then **actually look at the PNG**. Render one still per shot, plus one at each
transition. Check: is the subject in frame, is anything clipped mid-word, is
there dead space, does the text fit.

Add a silent composition (`defaultProps: { withAudio: false }`) so stills
don't need the audio file to exist.

**Tune numerically wherever you can.** Easing curves, scroll distances,
spectral content — these are all computable. Write a throwaway Python script
that samples the curve and prints what you'd otherwise be guessing at. It's
faster than a render and it's right.

Only render the full thing once the stills are right.

```bash
npx remotion render <CompositionId> out/video.mp4 --concurrency=4
```

Cap concurrency around 4 on a 16GB machine — Remotion spawns a Chrome tab per
slot and the default (core count) will swap.

---

## Phase 7 — Hand it over honestly

Send the file. Then say plainly:

- What you could not verify. You can read stills; you cannot judge how eight
  seconds *feels*, and you cannot hear the audio. Say so.
- **Any screen you reconstructed rather than observed** — especially on a
  gated product. List them, and offer to redo those beats if they'll share
  access.
- Where you made a judgement call they might disagree with.
- How to swap the music: drop any WAV or MP3 at `public/music.wav` and
  re-render.
- Anything you found in their product while building — a rendering bug, a
  wrong label, a missing state. You've just read their UI more carefully than
  most people ever will. That observation is often worth more than the video.

---

## Reference files

Read these when you reach the relevant phase — they're detailed and there's no
value in loading them all up front.

| file | when |
|---|---|
| `references/discovery.md` | Phase 1 — browsing, page triage, credentials, design systems, **and building from a gated product's landing page** |
| `references/structure.md` | Phase 2 — single narrative vs chapters, chapter-card design, writing feature labels, transitions, ordering |
| `references/camera.md` | Building shots — layout space, focus-point camera, cut vs push vs morph, isolating components |
| `references/motion.md` | Animation durations, typography, hook patterns, the question reel |
| `references/sound.md` | Sound design — the pop/swish/whoosh vocabulary, restraint, synthesizing keyboard and clicks |
| `references/music.md` | Sourcing vs synthesizing a bed, choosing a mood, aligning sections to cuts, mixing under the effects |
| `references/pitfalls.md` | **Read this before your first render.** Bugs that cost real hours, each with the fix. |

## Bundled scripts

`<skill-dir>` below is this skill's own directory — the path given to you when
the skill loaded. Don't assume a fixed install location; the skill may be
installed personally, as a plugin, or checked out into a project.

| script | what |
|---|---|
| `scripts/scaffold_video.py` | Creates the Remotion project with working version pins and config |
| `scripts/make_sfx.py` | Synthesizes a sound-effects track from a JSON event list. No samples, no dependencies beyond numpy. |
| `scripts/make_music.py` | Synthesizes a music bed in one of six moods, with its arrangement aligned to your cut. Same dependencies. |
| `assets/useCamera.ts` | The focus-point camera hook — copy into `src/hooks/` |
| `assets/ChapterCard.tsx` | Chapter card for the chaptered shape — copy into `src/components/` |

---

## The short version

Rebuild rather than record. One story, one artifact — unless the product is
gated or its features are genuinely separate, then three chapters with plain
labels. Ground every domain fact. Frames are the unit of everything. Isolate a
component rather than crop the page. UI motion is 150–300ms, camera moves are
~1s. Four sounds is plenty. Ask before you make music. Look at the stills
before you render. Say what you couldn't check, and what you inferred.
