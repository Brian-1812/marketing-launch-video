# Music

Sound effects mark moments. Music sets the register the whole film is read in
— whether the product feels urgent, calm, expensive, or friendly. It is the
single largest lever on how a cut *feels*, and it is the thing you are least
equipped to judge, because you cannot hear it.

So the order of operations matters more here than anywhere else.

---

## Get the track before you synthesize one

**Always ask first.** Most people have an opinion about music and many already
have a track. Asking costs one sentence and can save the entire audio effort:

> Do you want a music bed? If you have a track, send it and I'll cut to it. If
> not I can synthesize one — tell me the feel you want: energetic, calm,
> cinematic, minimal, warm, or tense.

Ranked, in order of how good the result will be:

| | source | when |
|---|---|---|
| 1 | **The user's own track** | Always the first ask. Free, licensed, theirs. |
| 2 | **A licensed library** — Artlist, Musicbed, Epidemic, Uppbeat | They have a subscription, or the launch justifies one. |
| 3 | **An AI music tool** — Suno, Udio | Only with the user's account and their explicit go-ahead. Never sign up for them. |
| 4 | **`scripts/make_music.py`** | Nothing else is available, or you need section changes that land on your cuts to the frame. |

A synthesized bed is a competent ambient bed. It is not a track anyone would
listen to on its own, and you should say so rather than letting someone
discover it at launch.

**If they give you a track, cut to it.** Find its BPM and its downbeats, set
the timeline's BPM to match, and move the shot boundaries onto its bars. That
is a much better film than a bed stretched under an existing edit.

---

## Choosing the mood

Mood follows from what the product *is*, not from what you find fun. When in
doubt, go calmer than your instinct — an overscored product video reads as an
advert, and a bed that is trying hard makes the product look like it needs the
help.

| mood | BPM | feel | fits |
|---|---|---|---|
| `energetic` | 124 | driving, full kit, bright plucks | dev tools, launches, anything with velocity as a selling point |
| `soft` | 88 | no kick, pad and bells, long tails | wellbeing, writing, journaling, healthcare |
| `cinematic` | 80 | wide, sub swells, risers, big room | enterprise, AI, infrastructure, anything selling scale |
| `minimal` | 110 | sub pulse and one pluck, lots of space | premium consumer, design tools, the Apple register |
| `warm` | 100 | major key, rhodes-ish, gentle swing | consumer, social, education, marketplaces |
| `tense` | 132 | phrygian, pulsing 16ths, no melody | security, observability, incident response |

Two rules that override the table:

**Serious subject matter takes a calmer bed.** A legal product, a medical
product, anything where a person is in trouble — `energetic` under that reads
as flippant. `minimal` or `cinematic`.

**Match the density of the visuals.** If the cut is fast and busy, the bed
must be sparse or the two fight. If the cut holds long still frames, the bed
can carry more.

---

## Align the music to the cut, not the other way round

This is the one thing a synthesized bed does better than a licensed track, so
use it. Every frame number in the spec comes from your timeline.

```json
{
  "fps": 60, "duration_frames": 2880, "bpm": 120,
  "mood": "minimal", "key": "A", "scale": "minor", "peak": 0.28,
  "sections": [
    {"at": 0,    "name": "intro", "layers": ["pad", "sub"]},
    {"at": 720,  "name": "build", "layers": ["pad", "sub", "bass", "pluck"]},
    {"at": 1560, "name": "main",  "layers": ["pad", "bass", "kick", "pluck", "bell"]},
    {"at": 2640, "name": "outro", "layers": ["pad", "bell"]}
  ],
  "hits":  [{"at": 1560, "riser": true}],
  "ducks": [{"from": 300, "to": 420, "depth": 0.7}]
}
```

```bash
python3 <skill-dir>/scripts/make_music.py music.spec.json public/music.wav
```

- **`sections`** — the arrangement. Put each `at` on the frame of a real shot
  boundary. Layers entering is how the film gains momentum; the classic shape
  is pad-only under the hook, bass in when the user acts, drums in when the
  product starts working, strip back to pad for the slate.
- **`hits`** — a riser into a frame plus an impact on it. Use exactly one, on
  your biggest cut. Two is one too many.
- **`ducks`** — pull the bed down under a held line, a beat of silence, or a
  moment you want read rather than felt. **This is the most underused tool
  here.** Music dropping out under a finished sentence is a stronger beat than
  anything you can add.

Layers available: `pad`, `sub`, `bass`, `pluck`, `bell`, `kick`, `hat`,
`clap`. Anything you leave out of a section's list simply isn't playing then.

The moods set BPM, key and scale, but `bpm`, `key`, `scale` in the spec
override them — and the BPM should be one whose beat is a whole number of
frames (at 60fps: 120 → 30 frames, 90 → 40, 80 → 45, 100 → 36).

---

## Sitting music and effects together

Two separate WAVs, two `<Audio>` tags. Keep them separate so either can be
replaced without regenerating the other.

```tsx
{withAudio ? (
  <>
    <Audio src={staticFile("music.wav")} volume={0.85} />
    <Audio src={staticFile("sfx.wav")} />
  </>
) : null}
```

The levels that work: **music at peak 0.28–0.32, effects at peak ~0.62.** The
bed should be quiet enough that you notice it only when it stops.

Frequency separation matters more than level. `make_music.py` already carves
2–5 kHz — that's where clicks, keystrokes and any voiceover live, and a bed
that is merely quiet still masks them. `make_sfx.py` correspondingly keeps
80–300 Hz nearly empty, where the kick and bass sit. If you bring your own
track, you don't get either carve, so drop the music another 3–4 dB.

If the user ever adds a voiceover, duck the music 6–8 dB under it. Don't rely
on it being quiet already.

---

## What went wrong last time, so it doesn't again

Two failures worth internalising, both from a real build:

**Additive sine pads whistle.** A chord built from pure sines has no harmonic
structure to mask its own beating, and the top partials read as a kettle. Use
band-limited saw stacks through a lowpass. `make_music.py` does this by
construction — and note that a naive `2*(t*f % 1) - 1` saw aliases badly,
folding harmonics back off Nyquist as inharmonic tones, which is a large part
of why cheap synthesis sounds cheap.

**Then the user rejected music entirely anyway**, and said they'd add their
own. Which is why "ask before you build" is at the top of this file. Spending
an hour on a bed nobody wanted is worse than spending a sentence asking.

Three things carry most of the quality difference in a synthesized bed, and
all three are in the script:

- **Reverb.** Dry oscillators sit flat at the front of the image with no
  apparent space. The same notes through even a crude synthesized room read as
  a recording of something. This is the biggest single lever.
- **Sidechain ducking.** Pulling the tonal layers down under each kick, even
  at a depth you wouldn't consciously notice, is most of what makes a bed feel
  like it has a pulse rather than being a drone with drums on top.
- **Not filling the grid.** Skipping a random third of the notes is what
  separates music from a placeholder loop.

---

## Verify by measuring

You cannot hear it. The script prints what you can actually check:

```
peak 0.300  RMS -26.0 dBFS  centroid 1017 Hz  width 0.46
energy  <120Hz  14.1%   120-2k  76.0%   2-5k   7.0%   >5k   2.7%
```

- **`<120 Hz` above ~40%** means it rumbles. Sub, kick and bass pile up down
  there; drop the sub gain or the kick.
- **`2-5k` above ~8%** means it will mask your clicks and keystrokes.
- **`width` near 0** means it's mono and will feel small. 0.4–0.8 is healthy.
- **RMS around −26 dBFS** at peak 0.30 is a normal bed. Much louder and it
  stops being background.

To confirm the arrangement actually lands where you said, measure the envelope
per section rather than trusting the spec:

```python
def rms(a, b):  # frames
    s = x[int(a/FPS*SR):int(b/FPS*SR)]
    return 20*np.log10(np.sqrt((s**2).mean()) + 1e-12)
```

A duck of `depth: 0.7` should show as roughly 7 dB down against its
neighbours. If it doesn't, the frame numbers are wrong.

Then hand it over honestly: say which judgements were measurements and which
were inference, and tell them that dropping any WAV or MP3 at
`public/music.wav` and re-rendering swaps it out.
