# marketing-launch-video

A Claude Code skill that produces a professional, animated launch video for a
software product — **given nothing but a URL**.

It browses the product, works out what it does, decides which screens carry the
story, rebuilds them as frame-driven React inside [Remotion](https://remotion.dev),
and choreographs camera, typography and sound into a 30–60 second cut.

```
/marketing-launch-video https://your-product.com
```

---

## The idea

**It rebuilds the UI rather than screen-recording it.**

Screen recordings fight you. Real latency is dead air, retakes are expensive,
you can't hold a frame or slow one beat and speed another, and you can't crop
tightly without hitting compression mush.

So the skill reads the product's actual DOM and CSS (or its source, if you have
it locally), reproduces the interface with the real class names and colours,
and drives every pixel from `useCurrentFrame()`. Typing lands on an exact
curve. A loading state resolves on the beat. A retake costs one number.

For surfaces that genuinely can't be rebuilt — a 3D viewer, a canvas, video
inside the product — it composites the real thing instead. In the 3D case it
renders your actual `.glb` through `@remotion/three`, frame by frame, which
looks better than any capture.

## What you get

- A standalone Remotion project (its own git repo — it never touches your
  product's source)
- A rendered MP4
- A synthesized sound-effects track, no samples or licensing
- An honest list of what couldn't be verified, and any bugs found in your
  product along the way

## Install

**As a plugin** (recommended — self-hosted, no submission to anyone):

```
/plugin marketplace add Brian-1812/marketing-launch-video
/plugin install marketing-launch-video
```

**Or as a personal skill:**

```bash
git clone https://github.com/Brian-1812/marketing-launch-video
cp -R marketing-launch-video/skills/marketing-launch-video ~/.claude/skills/
```

## Prerequisites

| | why |
|---|---|
| **Node 18+** | Remotion |
| **Python 3 + numpy** | the sound-effects synthesizer |
| **Chrome** | Remotion renders through headless Chrome |
| Browser automation *(optional)* | only needed for the URL-discovery step |
| `@gltf-transform/cli` *(optional)* | only if the product outputs 3D meshes |

### On Remotion's licence — read this

The videos are built with Remotion, which is **free for individuals and small
companies but requires a paid company licence** above a headcount threshold.
See [remotion.dev/license](https://remotion.dev/license). This skill doesn't
change that, and it's your responsibility to check whether your organisation
needs one. It's flagged here so nobody finds out after shipping a launch.

## What's in the box

```
skills/marketing-launch-video/
├── SKILL.md                  the workflow Claude follows
├── references/
│   ├── discovery.md          browsing a URL, triaging pages, the credentials conversation
│   ├── camera.md             layout space, the focus-point camera, cut vs push vs morph
│   ├── motion.md             durations, typography, hook patterns
│   ├── sound.md              pop / swish / whoosh, restraint, synthesizing keyboard
│   └── pitfalls.md           bugs that cost real hours, each with the fix
├── scripts/
│   ├── scaffold_video.py     creates the Remotion project with working version pins
│   └── make_sfx.py           synthesizes an SFX track from a JSON event list
└── assets/
    └── useCamera.ts          the focus-point camera hook
```

## A few things it knows that are easy to get wrong

**CSS `@keyframes` freeze at frame 0.** Remotion renders deterministically, so
wall-clock animations never advance. Every animation has to be re-expressed
against the frame.

**`delayRender()` at module scope fails the render** — it runs during bundle
evaluation, before there's a render scope. Stills work, then `render` blows up.

**A camera is a focus point, not a translate.** Shots are `{cx, cy, scale}` in
a fixed layout space, so you read coordinates off a still instead of guessing.

**Isolate a component rather than cropping the page.** Crop into an app to
reach the input and you get the input pinned to the frame edge with a
screenful of dead background — and at any readable scale it overflows.

**UI motion is 150–300ms.** Camera moves are ~1s. The contrast is what makes a
cut feel designed.

**Four sounds is usually plenty.** Scoring every beat produces wall-to-wall
noise. A pop means a thing appeared, a swish means an element moved inside the
shot, a whoosh means the *shot* moved. Most videos need three.

`references/pitfalls.md` has the rest.

## Contributing

Issues and PRs welcome — particularly:

- Product categories it handles badly (it's been exercised on chat-style AI
  tools and a 3D generator; a data-heavy dashboard or a CLI would stress it
  differently)
- Additional hook patterns in `motion.md`
- Pitfalls it should have known about

If you use it on something, a screenshot of what came out is genuinely useful
feedback.

## Licence

MIT — see [LICENSE](LICENSE).

Remotion, three.js and the fonts a generated project pulls in carry their own
licences.
