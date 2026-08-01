# Sound

## Restraint first

The instinct is to score every beat — a pop when each element appears, a swish
on each panel, a whoosh on each cut. The result is wall-to-wall noise that
makes a premium cut feel like a mobile game.

A 45-second product video usually needs **three to five sound events total**.
Something like:

1. One run of keyboard, for the first thing the user types
2. One click, when they send it
3. One click, when they open the artifact
4. Optionally: one texture under a signature motion (a reel, a long scroll)

Everything else is silence, and the silence is doing work. If a sound isn't
marking a moment you want the viewer to remember, cut it.

**Ask before adding music** — see `music.md`, which covers sourcing a bed,
choosing a mood, and aligning its arrangement to your cuts. Many people want
to drop their own track. Either way, build the effects track to sit under one:
leave 80–300 Hz effectively empty (that's where a kick and bass live) and
leave 6–10 dB of headroom. Effects peak ~0.62, music peak ~0.30.

---

## The vocabulary

These three get confused constantly, and using the wrong one is why UI audio
often feels off.

| | length | pitched | motion | means |
|---|---|---|---|---|
| **pop** | <100ms | yes, with an **upward** pitch bend | none | a thing came into existence |
| **swish** | 150–300ms | no — noise sweeping one way | short | an element moved *inside* the shot |
| **whoosh** | 400ms–1s | no — noise **arcing** up then down, an octave lower | large | the *shot* moved |

The pop's bend is its whole identity. The same envelope at a fixed frequency
is a notification beep; bent downward it means something failed or closed.

Rule of thumb: **pop = appearance, swish = movement in a shot, whoosh =
movement of the shot.** Use a whoosh on a panel and it feels like a wall
swinging shut; use a swish on a hard cut and the cut feels weightless.

For a whoosh on a cut, the arc's peak must land **on** the cut frame — start
it ~350ms early. The pre-roll is what makes a hard cut feel intentional rather
than abrupt.

---

## Keyboard

**Decouple audible strokes from rendered characters.** A hero line often types
at 25–30 characters/second because it has to fill the shot. Nobody types that.
One click per character is a zipper; one per character at half rate is a
machine gun.

Generate strokes from a humanised rhythm instead — mean interval ~128ms,
gaussian jitter σ ≈ 26ms, floor 70ms. That lands roughly one stroke per four
characters and reads as a competent person typing fast. Nobody counts
characters; they hear the rhythm. Break the grid with a longer gap where a
sentence ends.

**What makes a keyboard sound like "an iron machine"** — worth knowing,
because it's the most common failure:

- A low sine "thock" (150–200 Hz) with a long tail. It reads as a mechanical
  bottom-out in a resonant case, and it lands exactly where a music bed's kick
  lives. Replace it with band-limited noise around 360–680 Hz behind a steep
  (36 dB/oct) low skirt — you feel deck, not boom.
- A bright tick (3.5–7 kHz) with a very fast attack (<0.3ms). That's a step
  function to the ear: metal on metal. Slow the attack to ~0.7ms and drop its
  gain hard. **Slowing the attack of the brightest layer is the cheapest
  softness lever there is.**

Softer is not quieter: slower attacks lower the crest factor, so after
peak-normalising there is measurably *more* sound in the file.

Cut all layers of one stroke from the **same** noise vector. Correlated layers
fuse into a single object; independent noise per layer smears the transient,
which itself reads as machinery.

---

## Clicks

A mouse click needs a low housing resonance (~125 Hz, short) under the noise
burst. Without it you have a fingernail on glass.

**Fire the click ~35ms before the UI visibly reacts.** The ear expects cause
to precede effect; a click landing exactly on the state change reads as late.

Always include a release, quieter and brighter, ~42ms after. A click with no
release sounds broken.

---

## Synthesising it

`scripts/make_sfx.py` implements all of the above. It takes a JSON event list
and writes a WAV — no samples, no dependencies beyond numpy:

```bash
python3 <skill-dir>/scripts/make_sfx.py spec.json public/sfx.wav
```

```json
{
  "fps": 60,
  "duration_frames": 2880,
  "peak": 0.62,
  "events": [
    { "type": "typing", "from": 448, "to": 650, "text": "the line being typed" },
    { "type": "click",  "at": 720 },
    { "type": "click",  "at": 1536 },
    { "type": "reel",   "from": 0, "to": 290, "count": 44,
      "ease": [0.72, 0, 0.4, 1], "stages": "hold-step-hold-step-hold-spin" },
    { "type": "pop",    "at": 900, "bright": true },
    { "type": "swish",  "at": 1362, "pan": [0.85, 0.35] },
    { "type": "whoosh", "at": 1440 },
    { "type": "chime",  "at": 2520 }
  ]
}
```

Keep the event list in the video project next to the timeline, and keep its
frame numbers in sync with the beat table. If a beat moves, it moves in two
places.

---

## Two techniques worth reusing

**Rate-limit dense trains.** A slot-machine reel crossing ~0.8 items/frame
would fire ~70 detents/second, which is past where the ear resolves them and
turns to static. Drop anything closer than ~24ms to the previous one and let
the survivors get brighter and louder with velocity — it still reads as a
mechanism spinning up.

**Mirror the easing.** If a sound must land on the same frames as a visual
motion, re-implement the easing curve in the audio script rather than
approximating it. `make_sfx.py` includes a cubic-bezier solver for exactly
this.

---

## What you cannot verify

You cannot hear the output. Everything above is measurable — spectral
centroid, band energy distribution, envelope times — and you should measure it
rather than guess:

```python
X = np.abs(np.fft.rfft(run)); f = np.fft.rfftfreq(len(run), 1/SR)
centroid = (X*f).sum()/X.sum()
```

But say plainly which judgements were inference. "The centroid moved from 3.6
kHz to 2.6 kHz and the 80–300 Hz energy went from 43% to 0.3%" is a fact.
"It now sounds like a MacBook" is a guess.
