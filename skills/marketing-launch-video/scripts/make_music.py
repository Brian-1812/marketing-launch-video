#!/usr/bin/env python3
"""
Synthesize a background music bed for a product video, aligned to its cut.

    python3 make_music.py --mood energetic --bpm 120 --fps 60 --frames 2880 \
        --key A --scale minor --out public/music.wav

    python3 make_music.py music.spec.json public/music.wav     # full control

No samples, no dependencies beyond numpy. Every layer is oscillators, noise,
FFT-domain filtering, envelopes and a synthesized convolution reverb.

READ THIS BEFORE YOU USE IT
---------------------------
A synthesized bed is the FALLBACK, not the default. Ranked, the options are:

  1. The user's own track            — always ask first, it's free and it's theirs
  2. A licensed library track        — Artlist / Musicbed / Epidemic
  3. An AI music tool                — Suno / Udio, with the user's account and
                                       explicit permission
  4. This script                     — when nothing else is available, or when
                                       you need a bed that hits the cut exactly

What this is genuinely good at: sitting under a 45-second product film without
drawing attention, landing its section changes on your cuts to the frame, and
leaving the spectrum where your SFX live alone. What it is not: a track anyone
would listen to on its own. Set expectations accordingly, and say plainly that
you cannot hear it.

MOODS
-----
  energetic  driving, 124 BPM, full kit, bright plucks       launch / dev tools
  soft       calm, 88 BPM, no kick, pad + bells, long tails  wellbeing / writing
  cinematic  wide, 80 BPM, sub swells + risers, big room     enterprise / AI
  minimal    sparse, 110 BPM, sub pulse + one pluck          Apple-ish, premium
  warm       friendly, 100 BPM, major, rhodes-ish            consumer / social
  tense      urgent, 132 BPM, phrygian, pulsing 16ths        security / infra

SPEC (all fields optional except duration_frames)
-------------------------------------------------
{
  "fps": 60, "duration_frames": 2880, "bpm": 120,
  "mood": "energetic", "key": "A", "scale": "minor",
  "peak": 0.30,
  "sections": [
    {"at": 0,    "name": "intro", "layers": ["pad", "sub"]},
    {"at": 480,  "name": "build", "layers": ["pad", "bass", "hat"]},
    {"at": 960,  "name": "main",  "layers": ["pad", "bass", "kick", "hat",
                                             "pluck", "clap"]},
    {"at": 2640, "name": "outro", "layers": ["pad", "bell"]}
  ],
  "hits":  [{"at": 960, "riser": true}],
  "ducks": [{"from": 1080, "to": 1200, "depth": 0.6}]
}

`sections[].at`, `hits[].at` and `ducks` are FRAME numbers from your timeline,
so the arrangement changes land on the same frames as the cuts. Put them on
bar boundaries.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48_000
TABLE_N = 2048


# --------------------------------------------------------------------- theory

SEMI = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
        "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10,
        "Bb": 10, "B": 11}

SCALES = {
    "minor":    [0, 2, 3, 5, 7, 8, 10],
    "major":    [0, 2, 4, 5, 7, 9, 11],
    "dorian":   [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian":   [0, 2, 4, 6, 7, 9, 11],
}

# One progression per scale. Four bars, looped. These are deliberately the
# plainest possible choices — a bed that draws attention has failed.
PROGRESSIONS = {
    "minor":    [0, 5, 2, 6],   # i   VI  III VII
    "major":    [0, 4, 5, 3],   # I   V   vi  IV
    "dorian":   [0, 3, 0, 5],   # i   IV  i   VI
    "phrygian": [0, 1, 0, 6],   # i   II  i   VII
    "lydian":   [0, 4, 1, 4],   # I   V   ii  V
}


def degree_to_midi(root_midi: int, scale: list[int], degree: int) -> int:
    """Scale degrees extend past the octave, so degree 9 is the third, up one."""
    octave, idx = divmod(degree, len(scale))
    return root_midi + 12 * octave + scale[idx]


def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


# ----------------------------------------------------------------- primitives

def fft_band(x, lo, hi, lo_slope=12.0, hi_slope=18.0):
    """Band-limit in the frequency domain, skirts in dB/octave.

    Exact, fast, and — unlike an IIR run over a swept signal — introduces no
    phase seams. Same helper as make_sfx.py."""
    n = len(x)
    if n < 8:
        return x
    X = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(n, 1.0 / SR), 1e-6)
    below = np.minimum(1.0, (f / lo) ** (lo_slope / 6.0206))
    above = np.minimum(1.0, (hi / f) ** (hi_slope / 6.0206))
    return np.fft.irfft(X * below * above, n)


def _build_tables() -> list[tuple[float, np.ndarray]]:
    """Band-limited sawtooth wavetables, one per octave band.

    A naive `2*(t*f % 1) - 1` saw aliases badly: at 220 Hz its harmonics fold
    back off Nyquist as inharmonic tones, which is a large part of why cheap
    synthesis sounds cheap. Summing sin(n)/n up to Nyquist for the top of each
    band removes that by construction, and a wavetable makes it cheap enough to
    use per note."""
    ph = 2.0 * np.pi * np.arange(TABLE_N) / TABLE_N
    tables = []
    top = 27.5  # A0
    while top < 12000.0:
        max_h = max(1, int((SR / 2.2) / top))
        n = np.arange(1, max_h + 1)
        wave_ = (np.sin(np.outer(ph, n)) / n).sum(axis=1) * (2.0 / np.pi)
        tables.append((top * 2.0, wave_.astype(np.float64)))
        top *= 2.0
    return tables


_TABLES = _build_tables()


def saw(freq: float, n: int, phase: float = 0.0) -> np.ndarray:
    """Band-limited sawtooth, linear-interpolated out of a wavetable."""
    table = _TABLES[-1][1]
    for top, t in _TABLES:
        if freq < top:
            table = t
            break
    pos = (phase * TABLE_N + np.arange(n) * (freq / SR) * TABLE_N) % TABLE_N
    i0 = pos.astype(np.int64)
    frac = pos - i0
    i1 = (i0 + 1) % TABLE_N
    return table[i0] * (1.0 - frac) + table[i1] * frac


def sine(freq: float, n: int, phase: float = 0.0) -> np.ndarray:
    t = np.arange(n) / SR
    return np.sin(2.0 * np.pi * (freq * t + phase))


def noise(n: int, rng) -> np.ndarray:
    return rng.standard_normal(n)


def adsr(n, atk_ms, dec_ms, sus, rel_ms):
    """Attack / decay / sustain / release, sample-accurate.

    The release is carved out of the END of the note, so a note is exactly the
    length you asked for and adjacent notes never overlap unintentionally."""
    a = min(n, max(1, int(SR * atk_ms / 1000.0)))
    d = min(n - a, max(1, int(SR * dec_ms / 1000.0)))
    r = min(n - a - d, max(1, int(SR * rel_ms / 1000.0)))
    s = max(0, n - a - d - r)
    return np.concatenate([
        np.linspace(0.0, 1.0, a) ** 1.6,
        np.linspace(1.0, sus, d),
        np.full(s, sus),
        np.linspace(sus, 0.0, r) ** 1.8,
    ])[:n]


def decay_env(n, atk_ms, tau_ms):
    t = np.arange(n) / SR
    a = max(1, int(SR * atk_ms / 1000.0))
    ramp = np.ones(n)
    ramp[:a] = np.linspace(0.0, 1.0, a)
    return np.exp(-t / (tau_ms / 1000.0)) * ramp


# --------------------------------------------------------------------- reverb

def make_ir(seconds: float, decay: float, brightness: float, rng) -> np.ndarray:
    """A synthesized room.

    This is the single biggest lever between "sounds programmed" and "sounds
    produced". Dry oscillators sit flat at the front of the image with no
    apparent space; the same notes through even a crude room read as a
    recording of something.

    Exponentially-decaying noise is the whole trick, plus two things that stop
    it sounding like a hiss gate: a short pre-delay (so the direct sound is
    distinct from the room) and a handful of discrete early reflections."""
    n = int(SR * seconds)
    t = np.arange(n) / SR
    tail = noise(n, rng) * np.exp(-t * decay)
    # Damping: rooms lose highs faster than lows, so darken over time.
    dark = fft_band(tail, 60.0, 1600.0, 6, 8)
    bright = fft_band(tail, 90.0, 1600.0 + 7000.0 * brightness, 6, 8)
    blend = np.exp(-t * decay * 1.7)[:n]
    ir = bright * blend + dark * (1.0 - blend)
    # Early reflections.
    for delay_ms, g in ((11.0, 0.5), (17.0, -0.38), (29.0, 0.3), (41.0, -0.22)):
        d = int(SR * delay_ms / 1000.0)
        if d < n:
            ir[d] += g
    pre = int(SR * 0.012)
    ir = np.concatenate([np.zeros(pre), ir])[:n]
    return ir / (np.sqrt(np.sum(ir ** 2)) + 1e-9)


def convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    n = len(x) + len(ir) - 1
    size = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)
    return y[: len(x)]


# ---------------------------------------------------------------------- moods

MOODS = {
    "energetic": dict(
        bpm=124, scale="minor", root="A", oct_pad=4, brightness=0.85,
        pad_cut=(150, 3400), swing=0.0, room=1.5, decay=4.2, wet_pad=0.30,
        drums=True, kick_pattern="four", hat_div=8, pluck_div=8,
        pluck_gain=0.32, bell_gain=0.0, density=1.0, duck=0.42,
    ),
    "soft": dict(
        bpm=88, scale="major", root="F", oct_pad=4, brightness=0.35,
        pad_cut=(110, 1900), swing=0.08, room=3.2, decay=1.9, wet_pad=0.55,
        drums=False, kick_pattern="none", hat_div=0, pluck_div=4,
        pluck_gain=0.14, bell_gain=0.26, density=0.45, duck=0.0,
    ),
    "cinematic": dict(
        bpm=80, scale="minor", root="D", oct_pad=3, brightness=0.5,
        pad_cut=(70, 2400), swing=0.0, room=4.5, decay=1.3, wet_pad=0.62,
        drums=True, kick_pattern="half", hat_div=0, pluck_div=0,
        pluck_gain=0.0, bell_gain=0.22, density=0.5, duck=0.30,
    ),
    "minimal": dict(
        bpm=110, scale="minor", root="C", oct_pad=4, brightness=0.6,
        pad_cut=(120, 2600), swing=0.0, room=2.4, decay=2.6, wet_pad=0.42,
        drums=True, kick_pattern="half", hat_div=0, pluck_div=4,
        pluck_gain=0.22, bell_gain=0.18, density=0.35, duck=0.26,
    ),
    "warm": dict(
        bpm=100, scale="major", root="G", oct_pad=4, brightness=0.55,
        pad_cut=(120, 2600), swing=0.12, room=2.2, decay=2.4, wet_pad=0.42,
        drums=True, kick_pattern="soft", hat_div=8, pluck_div=8,
        pluck_gain=0.20, bell_gain=0.24, density=0.7, duck=0.30,
    ),
    "tense": dict(
        bpm=132, scale="phrygian", root="E", oct_pad=3, brightness=0.7,
        pad_cut=(90, 2200), swing=0.0, room=2.0, decay=3.0, wet_pad=0.34,
        drums=True, kick_pattern="four", hat_div=16, pluck_div=16,
        pluck_gain=0.18, bell_gain=0.0, density=1.0, duck=0.50,
    ),
}

DEFAULT_LAYERS = {
    "intro": ["pad", "sub"],
    "build": ["pad", "sub", "bass", "hat"],
    "main":  ["pad", "bass", "kick", "hat", "pluck", "clap"],
    "outro": ["pad", "bell"],
}


# ------------------------------------------------------------------ the track

class Music:
    def __init__(self, spec: dict):
        self.fps = spec.get("fps", 60)
        self.frames = int(spec["duration_frames"])
        self.mood_name = spec.get("mood", "minimal")
        if self.mood_name not in MOODS:
            raise SystemExit(f"unknown mood {self.mood_name!r}; "
                             f"choose from {', '.join(MOODS)}")
        m = dict(MOODS[self.mood_name])
        m.update({k: v for k, v in spec.items()
                  if k in m and v is not None})
        self.m = m

        self.bpm = spec.get("bpm") or m["bpm"]
        self.scale_name = spec.get("scale") or m["scale"]
        self.scale = SCALES[self.scale_name]
        self.prog = PROGRESSIONS.get(self.scale_name, PROGRESSIONS["minor"])
        root_name = spec.get("key") or m["root"]
        self.root = 12 * (m["oct_pad"] + 1) + SEMI[root_name]

        self.n = int(SR * self.frames / self.fps)
        self.rng = np.random.default_rng(spec.get("seed", 20260801))

        self.spb = 60.0 / self.bpm            # seconds per beat
        self.bar = self.spb * 4.0

        # Buses, stereo. Kept separate so the kick can duck the tonal material
        # and so each gets its own reverb send.
        self.tonal = np.zeros((2, self.n))
        self.perc = np.zeros((2, self.n))
        self.sub_bus = np.zeros((2, self.n))
        self.kick_times: list[float] = []

        self.sections = self._resolve_sections(spec.get("sections"))
        self.hits = spec.get("hits", [])
        self.ducks = spec.get("ducks", [])

    # -- arrangement --

    def _resolve_sections(self, given):
        """Sections are FRAME-aligned so the arrangement changes land on cuts.

        With none given, fall back to a generic intro/build/main/outro over the
        whole duration — usable, but the point of this script is that you pass
        your actual shot boundaries."""
        if given:
            secs = sorted(
                [{"at": int(s["at"]),
                  "name": s.get("name", "main"),
                  "layers": s.get("layers") or DEFAULT_LAYERS.get(
                      s.get("name", "main"), DEFAULT_LAYERS["main"])}
                 for s in given],
                key=lambda s: s["at"])
        else:
            q = self.frames
            secs = [
                {"at": 0, "name": "intro", "layers": DEFAULT_LAYERS["intro"]},
                {"at": int(q * 0.15), "name": "build",
                 "layers": DEFAULT_LAYERS["build"]},
                {"at": int(q * 0.32), "name": "main",
                 "layers": DEFAULT_LAYERS["main"]},
                {"at": int(q * 0.88), "name": "outro",
                 "layers": DEFAULT_LAYERS["outro"]},
            ]
        for i, s in enumerate(secs):
            s["until"] = secs[i + 1]["at"] if i + 1 < len(secs) else self.frames
        return secs

    def layers_at(self, t: float) -> list[str]:
        f = t * self.fps
        for s in self.sections:
            if s["at"] <= f < s["until"]:
                return s["layers"]
        return self.sections[-1]["layers"] if self.sections else []

    # -- placement --

    def add(self, bus: np.ndarray, seg: np.ndarray, t: float, gain: float,
            pan: float = 0.0):
        """Constant-power pan into a stereo bus."""
        i = int(t * SR)
        if i >= self.n or gain <= 0:
            return
        if i < 0:
            seg = seg[-i:]
            i = 0
        seg = seg[: self.n - i] * gain
        th = (pan + 1.0) * math.pi / 4.0
        bus[0, i:i + seg.size] += seg * math.cos(th) * 1.4142
        bus[1, i:i + seg.size] += seg * math.sin(th) * 1.4142

    # -- instruments --

    def pad(self, midis: list[int], dur: float) -> np.ndarray:
        """Detuned saw stack through a lowpass. The chord bed.

        Seven voices at odd cent offsets: the beating between them is what
        gives a static chord any life at all. A single saw per note is a
        video-game organ."""
        n = int(SR * dur)
        lo, hi = self.m["pad_cut"]
        out = np.zeros(n)
        cents = [-11.0, -6.5, -2.0, 0.0, 2.5, 7.0, 12.0]
        for mid in midis:
            f0 = hz(mid)
            for c in cents:
                f = f0 * 2.0 ** (c / 1200.0)
                out += saw(f, n, phase=self.rng.random()) / (len(cents) * 1.6)
        # Deliberately no sub-octave here. One per chord tone stacks three or
        # four sines below 80 Hz and the bed turns into a rumble; the sub bus
        # owns that register alone.
        out = fft_band(out, lo, hi, 12, 14)
        return out * adsr(n, 380, 260, 0.82, int(dur * 1000 * 0.32))

    def bass(self, midi: int, dur: float) -> np.ndarray:
        n = int(SR * dur)
        f = hz(midi)
        body = sine(f, n) * 0.8 + saw(f, n) * 0.22 + sine(f * 2, n) * 0.12
        body = fft_band(body, 34.0, 420.0, 18, 16)
        return body * adsr(n, 8, 90, 0.75, int(dur * 1000 * 0.30))

    def pluck(self, midi: int, dur: float) -> np.ndarray:
        n = int(SR * dur)
        f = hz(midi)
        b = self.m["brightness"]
        x = saw(f, n, self.rng.random()) * 0.7 + sine(f * 2, n) * 0.2
        x = fft_band(x, f * 0.85, 900.0 + 4200.0 * b, 14, 12)
        return x * decay_env(n, 3.0, 90.0 + 160.0 * (1.0 - b))

    def bell(self, midi: int, dur: float) -> np.ndarray:
        """Sine plus two inharmonic partials — the 2.76 and 5.40 ratios are
        roughly where a struck bar sits, and they're what stops a pure sine
        reading as a test tone."""
        n = int(SR * dur)
        f = hz(midi)
        x = (sine(f, n) + 0.34 * sine(f * 2.76, n) + 0.16 * sine(f * 5.40, n)
             + 0.08 * sine(f * 8.93, n))
        return x * decay_env(n, 1.5, 620.0)

    def sub(self, midi: int, dur: float) -> np.ndarray:
        n = int(SR * dur)
        return sine(hz(midi - 12), n) * adsr(n, 90, 200, 0.7,
                                             int(dur * 1000 * 0.4))

    # -- percussion --

    def kick(self, soft=False) -> np.ndarray:
        n = int(SR * 0.42)
        t = np.arange(n) / SR
        # Pitch sweep, integrated so the bend is right (multiplying t by a
        # varying f gives the wrong curve — the classic mistake).
        f = 48.0 + 95.0 * np.exp(-t / 0.021)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR)
        body *= np.exp(-t / (0.16 if not soft else 0.10))
        click = fft_band(noise(int(SR * 0.006), self.rng), 900, 5200)
        click = click * decay_env(len(click), 0.4, 2.4) * (0.12 if not soft else 0.05)
        out = body * (0.9 if not soft else 0.5)
        out[: len(click)] += click
        return out

    def hat(self, open_=False) -> np.ndarray:
        n = int(SR * (0.18 if open_ else 0.05))
        x = fft_band(noise(n, self.rng), 6200, 13500, 24, 10)
        return x * decay_env(n, 0.6, 42.0 if open_ else 15.0)

    def clap(self) -> np.ndarray:
        n = int(SR * 0.30)
        out = np.zeros(n)
        # Three short bursts a few ms apart plus a tail — one burst is a
        # snare-ish tick, three read as hands.
        for d_ms, g in ((0.0, 1.0), (8.0, 0.8), (17.0, 0.62)):
            d = int(SR * d_ms / 1000.0)
            b = fft_band(noise(int(SR * 0.012), self.rng), 1100, 3400, 18, 12)
            out[d:d + len(b)] += b * decay_env(len(b), 0.5, 5.0) * g
        tail = fft_band(noise(n, self.rng), 1300, 3000, 14, 10)
        return out + tail * decay_env(n, 2.0, 62.0) * 0.35

    def riser(self, dur: float) -> np.ndarray:
        """Noise whose passband climbs into the hit. Blocked rather than
        smooth because a time-varying FFT filter has to be, and at 24 blocks
        per second the seams are inaudible under a bed."""
        n = int(SR * dur)
        src = noise(n, self.rng)
        blocks = max(8, int(dur * 24))
        step = n // blocks
        out = np.zeros(n)
        for b in range(blocks):
            i, j = b * step, min(n, (b + 1) * step + 1)
            p = b / max(1, blocks - 1)
            lo = 220.0 * (1.0 - p) + 2600.0 * p
            out[i:j] = fft_band(src[i:j], lo, lo * 2.6, 20, 14)
        t = np.arange(n) / SR
        return out * (t / (dur + 1e-9)) ** 2.2

    def impact(self) -> np.ndarray:
        n = int(SR * 1.6)
        t = np.arange(n) / SR
        f = 44.0 + 60.0 * np.exp(-t / 0.05)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.42)
        crack = fft_band(noise(int(SR * 0.25), self.rng), 200, 4000, 12, 10)
        out = body * 0.85
        out[: len(crack)] += crack * decay_env(len(crack), 1.0, 55.0) * 0.30
        return out

    # -- the arranger --

    def build(self):
        m = self.m
        total_s = self.n / SR
        bars = int(math.ceil(total_s / self.bar))

        for b in range(bars):
            t0 = b * self.bar
            if t0 >= total_s:
                break
            layers = self.layers_at(t0 + 0.01)
            deg = self.prog[b % len(self.prog)]
            triad = [degree_to_midi(self.root, self.scale, deg + i)
                     for i in (0, 2, 4)]
            # A 7th on every other bar, so four bars of the same voicing don't
            # read as a loop.
            chord = triad + ([degree_to_midi(self.root, self.scale, deg + 6)]
                             if b % 2 == 1 else [])
            root_midi = triad[0] - 24

            if "pad" in layers:
                # Rendered twice and panned hard. The two calls draw different
                # random phases, so the sides are decorrelated and the chord
                # occupies the whole image instead of a point in the middle.
                self.add(self.tonal, self.pad(chord, self.bar * 1.02),
                         t0, 0.34, pan=-0.55)
                self.add(self.tonal, self.pad(chord, self.bar * 1.02),
                         t0, 0.34, pan=+0.55)
            if "sub" in layers:
                self.add(self.sub_bus, self.sub(root_midi, self.bar * 0.9),
                         t0, 0.20)
            if "bass" in layers:
                for beat in self._bass_beats():
                    note = root_midi if beat in (0.0, 2.0) else root_midi + 7
                    self.add(self.tonal,
                             self.bass(note, self.spb * 0.9),
                             t0 + beat * self.spb, 0.24)
            if "pluck" in layers and m["pluck_div"]:
                self._plucks(t0, chord, m["pluck_div"])
            if "bell" in layers and m["bell_gain"] > 0:
                pick = chord[(b // 2) % len(chord)] + 12
                self.add(self.tonal, self.bell(pick, 2.2),
                         t0 + self.spb * (0 if b % 2 == 0 else 2),
                         m["bell_gain"])
            if "kick" in layers and m["drums"]:
                self._kicks(t0)
            if "hat" in layers and m["hat_div"]:
                self._hats(t0, m["hat_div"])
            if "clap" in layers and m["drums"]:
                for beat in (1.0, 3.0):
                    self.add(self.perc, self.clap(), t0 + beat * self.spb, 0.20)

        self._hits()

    def _bass_beats(self):
        d = self.m["density"]
        if d >= 0.9:
            return [0.0, 1.5, 2.0, 3.5]
        if d >= 0.6:
            return [0.0, 2.0, 3.5]
        return [0.0, 2.0]

    def _grid(self, t0, div):
        """Positions of a `div`-per-bar grid, with swing pushing the offbeats
        late. Straight math: the k-th step, plus a fraction of a step if k is
        odd. Anything cleverer drifts."""
        step = 4.0 / div * self.spb
        for k in range(div):
            yield k, t0 + k * step + (self.m["swing"] * step if k % 2 else 0.0)

    def _plucks(self, t0, chord, div):
        step = 4.0 / div * self.spb
        notes = [c + 12 for c in chord]
        for k, t in self._grid(t0, div):
            # Skip roughly (1 - density) of the grid, but never the downbeat.
            # A fully-filled grid is most of what makes a bed sound like a
            # placeholder loop.
            if k and self.rng.random() > self.m["density"] * 0.8:
                continue
            n = notes[(k * 2) % len(notes)]
            self.add(self.tonal, self.pluck(n, step * 1.8), t,
                     self.m["pluck_gain"] * (1.0 if k % 4 == 0 else 0.72),
                     pan=-0.45 if k % 2 else 0.45)

    def _kicks(self, t0):
        pat = self.m["kick_pattern"]
        soft = pat == "soft"
        beats = {"four": [0.0, 1.0, 2.0, 3.0],
                 "half": [0.0, 2.0],
                 "soft": [0.0, 2.0],
                 "none": []}[pat]
        for beat in beats:
            t = t0 + beat * self.spb
            self.add(self.perc, self.kick(soft), t, 0.34 if not soft else 0.22)
            self.kick_times.append(t)

    def _hats(self, t0, div):
        for k, t in self._grid(t0, div):
            if self.rng.random() > 0.85:
                continue
            open_ = (k % div) == div - 2
            g = 0.16 if k % 2 == 0 else 0.10
            self.add(self.perc, self.hat(open_), t,
                     g * (1.4 if open_ else 1.0),
                     pan=self.rng.uniform(-0.25, 0.25))

    def _hits(self):
        for h in self.hits:
            t = h["at"] / self.fps
            if h.get("riser", True):
                dur = h.get("riser_seconds", self.bar)
                self.add(self.perc, self.riser(dur), t - dur,
                         h.get("riser_gain", 0.20))
            self.add(self.perc, self.impact(), t, h.get("gain", 0.42))

    # -- mix --

    def mix(self, peak: float):
        m = self.m
        # Two independent impulses. A single IR convolved into both sides
        # collapses the tail to the centre and undoes the panning above; two
        # decorrelated tails are what a real room does.
        irs = [make_ir(m["room"], m["decay"], m["brightness"], self.rng)
               for _ in range(2)]

        tonal = np.stack([self.tonal[c] + convolve(self.tonal[c], irs[c])
                          * m["wet_pad"] for c in range(2)])
        perc = np.stack([self.perc[c] + convolve(self.perc[c], irs[c]) * 0.12
                         for c in range(2)])

        # Sidechain: duck the tonal material under each kick. Even at a depth
        # you would not consciously notice, this is most of what makes a bed
        # feel like it has a pulse rather than a drone with drums on top.
        if self.kick_times and m["duck"] > 0:
            duck = np.ones(self.n)
            span = int(SR * 0.5)
            shape = 1.0 - m["duck"] * np.exp(-np.arange(span) / SR / 0.14)
            for t in self.kick_times:
                i = int(t * SR)
                if i < self.n:
                    seg = shape[: self.n - i]
                    duck[i:i + seg.size] = np.minimum(duck[i:i + seg.size], seg)
            tonal *= duck
            self.sub_bus *= duck

        stereo = (tonal + perc + self.sub_bus).T.copy()

        f = np.maximum(np.fft.rfftfreq(self.n, 1.0 / SR), 1e-6)
        # Carve 2-5 kHz. That band is where clicks, keystrokes and any
        # voiceover live; a bed that is merely quiet still masks them.
        shape = 1.0 - 0.26 * np.exp(-((np.log2(f / 3200.0)) ** 2) / 0.55)
        # Low shelf. Sub, kick and bass all pile up under 120 Hz and without
        # this the bed measures 50-80% of its energy down there, which reads
        # as rumble on anything with real speakers.
        shape *= 1.0 / (1.0 + 1.9 / (1.0 + (f / 105.0) ** 2.4))
        for c in range(2):
            stereo[:, c] = np.fft.irfft(np.fft.rfft(stereo[:, c]) * shape,
                                        self.n)

        # Glue. tanh at this level is inaudible as distortion but pulls the
        # peaks in, so normalising afterwards leaves the body louder.
        stereo = np.tanh(stereo * 1.25) / 1.25
        for c in range(2):
            stereo[:, c] = fft_band(stereo[:, c], 28.0, 15500.0, 12, 10)

        # Fades. A bed that starts at full level reads as a mistake.
        fi = int(SR * 1.2)
        fo = int(SR * 2.0)
        stereo[:fi] *= np.linspace(0, 1, fi)[:, None] ** 1.5
        stereo[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.4

        # User ducks — drop the bed under a held line or a silent beat.
        for d_ in self.ducks:
            i, j = int(d_["from"] / self.fps * SR), int(d_["to"] / self.fps * SR)
            i, j = max(0, i), min(self.n, j)
            if j <= i:
                continue
            depth = 1.0 - d_.get("depth", 0.6)
            ramp = int(min((j - i) / 2, SR * 0.35))
            g = np.full(j - i, depth)
            g[:ramp] = np.linspace(1.0, depth, ramp)
            g[-ramp:] = np.linspace(depth, 1.0, ramp)
            stereo[i:j] *= g[:, None]

        pk = float(np.max(np.abs(stereo)))
        if pk > 0:
            stereo *= peak / pk
        return stereo

    def write(self, path, peak=0.30):
        self.build()
        stereo = self.mix(peak)
        pcm = (np.clip(stereo, -1, 1) * 32767.0).astype("<i2")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        return stereo


def report(stereo, spec, path):
    mono = stereo.mean(axis=1)
    side = (stereo[:, 0] - stereo[:, 1]) / 2.0
    rms = float(np.sqrt(np.mean(mono ** 2)))
    P = np.abs(np.fft.rfft(mono)) ** 2
    f = np.fft.rfftfreq(len(mono), 1.0 / SR)
    # Power-weighted, so the centroid and the band table below agree. A
    # magnitude-weighted centroid is dragged upward by broadband hiss that
    # carries almost no energy, and reports 5 kHz for a track that is mostly
    # bass.
    centroid = float((P * f).sum() / (P.sum() + 1e-9))

    def band(lo, hi):
        return 100.0 * P[(f >= lo) & (f < hi)].sum() / (P.sum() + 1e-9)

    width = float(np.sqrt(np.mean(side ** 2)) / (rms + 1e-12))

    print(f"wrote {path}")
    print(f"  {len(mono)/SR:.2f}s, {SR} Hz stereo, mood={spec.get('mood')}, "
          f"{spec.get('bpm')} BPM, {spec.get('key')} {spec.get('scale')}")
    print(f"  peak {float(np.max(np.abs(stereo))):.3f}  "
          f"RMS {20*math.log10(rms+1e-12):.1f} dBFS  "
          f"centroid {centroid:.0f} Hz  width {width:.2f}")
    print(f"  energy  <120Hz {band(20,120):5.1f}%   120-2k {band(120,2000):5.1f}%"
          f"   2-5k {band(2000,5000):5.1f}%   >5k {band(5000,20000):5.1f}%")
    print("  targets: <120Hz under ~40% (else it rumbles), 2-5k under ~8%")
    print("  (2-5k is where clicks, keys and voice sit — leave it for them)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?", help="JSON spec file")
    ap.add_argument("out_positional", nargs="?", help="output WAV")
    ap.add_argument("--out")
    ap.add_argument("--mood", choices=sorted(MOODS))
    ap.add_argument("--bpm", type=int)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--frames", type=int)
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--key")
    ap.add_argument("--scale", choices=sorted(SCALES))
    ap.add_argument("--peak", type=float, default=0.30,
                    help="Final true peak. Keep low — this sits UNDER the SFX.")
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()

    spec: dict = {}
    out = a.out or a.out_positional
    if a.spec and a.spec.endswith(".json"):
        spec = json.loads(Path(a.spec).read_text())
    elif a.spec and not out:
        out = a.spec

    for k, v in (("mood", a.mood), ("bpm", a.bpm), ("key", a.key),
                 ("scale", a.scale), ("seed", a.seed)):
        if v is not None:
            spec[k] = v
    if a.fps:
        spec.setdefault("fps", a.fps)
    if a.frames:
        spec["duration_frames"] = a.frames
    elif a.seconds:
        spec["duration_frames"] = int(a.seconds * spec.get("fps", 60))
    if "duration_frames" not in spec:
        ap.error("need --frames, --seconds, or duration_frames in the spec")
    if not out:
        ap.error("need an output path (--out or positional)")

    music = Music(spec)
    spec.setdefault("mood", music.mood_name)
    spec["bpm"], spec["scale"] = music.bpm, music.scale_name
    spec.setdefault("key", music.m["root"])
    stereo = music.write(out, spec.get("peak", a.peak))
    report(stereo, spec, out)

    print("\n  sections:")
    for s in music.sections:
        print(f"    f{s['at']:>5}-{s['until']:<5} {s['name']:<8} "
              f"{', '.join(s['layers'])}")
    print("\n  You cannot hear this. Say so when you hand it over, and offer "
          "the swap-in path:\n  drop any WAV/MP3 at the same path and re-render.")


if __name__ == "__main__":
    main()
