#!/usr/bin/env python3
"""
Synthesize a sound-effects track for a product video from a JSON event list.

    python3 make_sfx.py spec.json out/sfx.wav

No samples and no dependencies beyond numpy — every sound is oscillators,
white noise, FFT-domain filtering and envelopes. That means it is fully
reproducible and every parameter is tunable.

SPEC
----
{
  "fps": 60,
  "duration_frames": 2880,
  "peak": 0.62,              // final true peak; leave headroom for music
  "events": [
    {"type": "typing", "from": 448, "to": 650, "text": "the typed line"},
    {"type": "click",  "at": 720},
    {"type": "reel",   "from": 0, "to": 290, "count": 44,
                       "ease": [0.72, 0, 0.4, 1], "staged": true},
    {"type": "pop",    "at": 900, "bright": false},
    {"type": "swish",  "at": 1362, "pan": [0.85, 0.35]},
    {"type": "whoosh", "at": 1440},
    {"type": "chime",  "at": 2520}
  ]
}

RESTRAINT IS THE POINT. A 45-second video usually needs three to five events.
Scoring every beat produces wall-to-wall noise that makes a premium cut feel
like a mobile game. See references/sound.md.
"""

from __future__ import annotations

import json
import math
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48_000


# --- primitives -------------------------------------------------------------

def fft_band(x, lo, hi, lo_slope=12.0, hi_slope=18.0):
    """Band-limit in the frequency domain, skirts in dB/octave.

    Doing this with an FFT rather than an IIR loop keeps it exact, keeps it
    fast, and — for the sweeps below — introduces no phase seams."""
    n = len(x)
    if n < 8:
        return x
    X = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(n, 1.0 / SR), 1e-6)
    below = np.minimum(1.0, (f / lo) ** (lo_slope / 6.0206))
    above = np.minimum(1.0, (hi / f) ** (hi_slope / 6.0206))
    return np.fft.irfft(X * below * above, n)


def env(n, atk_ms, tau_ms):
    """Linear attack into an exponential decay."""
    t = np.arange(n) / SR
    a = max(1, int(SR * atk_ms / 1000.0))
    ramp = np.ones(n)
    ramp[:a] = np.linspace(0.0, 1.0, a)
    return np.exp(-t / (tau_ms / 1000.0)) * ramp


def norm(x):
    return x / (np.max(np.abs(x)) + 1e-9)


def bent_sine(n, f_start, f_end, tau_ms):
    """A sine whose frequency bends. Phase must be the INTEGRAL of frequency —
    multiplying t by a varying f gives the wrong bend, which is the most
    common way this sound is got wrong."""
    t = np.arange(n) / SR
    f = f_end + (f_start - f_end) * np.exp(-t / (tau_ms / 1000.0))
    return np.sin(2 * math.pi * np.cumsum(f) / SR)


def sweep_noise(dur_s, f_lo, f_hi, bands, q, arc=False, rng=None):
    """Noise through a travelling passband — the swish/whoosh primitive.

    N full-length band copies crossfaded by a triangular weight, NOT chunked
    filtering. Chunking leaves an audible seam at every boundary."""
    rng = rng or np.random.default_rng(0)
    n = int(dur_s * SR)
    src = rng.standard_normal(n)
    centres = np.geomspace(f_lo, f_hi, bands)
    copies = [fft_band(src, c / q, c * q) for c in centres]
    t = np.linspace(0.0, 1.0, n)
    traj = (
        f_lo * (f_hi / f_lo) ** (np.sin(math.pi * t) ** 1.1)
        if arc
        else f_lo * (f_hi / f_lo) ** t
    )
    log_c = np.log2(centres)
    step = log_c[1] - log_c[0]
    out = np.zeros(n)
    lt = np.log2(traj)
    for k in range(bands):
        out += copies[k] * np.clip(1.0 - np.abs(lt - log_c[k]) / step, 0.0, 1.0)
    return out


def bezier_y(x, x1, y1, x2, y2):
    """CSS cubic-bezier: solve x(t)=x by bisection, return y(t).

    Lets the audio land on exactly the frames a CSS/Remotion easing puts a
    visual on. Mirror the curve rather than approximating it."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bx = lambda t: 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t * t * x2 + t ** 3
    by = lambda t: 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t * t * y2 + t ** 3
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if bx(mid) < x:
            lo = mid
        else:
            hi = mid
    return by((lo + hi) / 2)


# --- the palette ------------------------------------------------------------

class Kit:
    def __init__(self, rng):
        self.rng = rng

    def noise(self, n):
        return self.rng.standard_normal(n)

    def key_down(self, seed, heavy=False):
        """A scissor switch on an aluminium laptop deck, close-mic'd and dry.

        Deliberately has NO low sine "thock". A 150-200 Hz sine with a long
        tail reads as a mechanical bottom-out in a resonant case — that is the
        "iron machine" quality — and it sits exactly where a music bed's kick
        lives. Weight comes from a noise plate behind a steep low skirt
        instead: you feel deck, not boom.

        All three layers are cut from the SAME noise vector. Correlated layers
        fuse into one object; independent noise per layer smears the transient,
        which itself reads as machinery."""
        r = np.random.default_rng(1000 + seed)
        dur = 0.026 * r.uniform(0.92, 1.08) * (1.15 if heavy else 1.0)
        n = int(dur * SR)
        bw = r.uniform(0.95, 1.05) * (0.88 if heavy else 1.0)
        src = self.noise(n)

        deck = norm(fft_band(src, 700 * bw, 2400 * bw, 24, 14)
                    * env(n, 0.8 * r.uniform(0.85, 1.15), 4.2 * r.uniform(0.9, 1.1)))
        plate = norm(fft_band(src, 360 * bw, 680 * bw, 36, 18)
                     * env(n, 1.6, 6.5 * r.uniform(0.9, 1.1)))
        # Widest randomisation of the three: varying brightness stroke to
        # stroke is what reads as different keys under different fingers.
        air = norm(fft_band(src, 3200 * bw, 7200 * bw, 10, 12)
                   * env(n, 0.7, 1.6 * r.uniform(0.9, 1.1)))

        out = (deck
               + plate * 0.34 * r.uniform(0.7, 1.2) * (1.6 if heavy else 1.0)
               + air * 0.13 * r.uniform(0.6, 1.25))
        # Protect the bass zone; take the fizz off the top.
        return norm(fft_band(out, 320.0, 5500.0, 30, 9)) * r.uniform(0.8, 1.0)

    def key_up(self, seed):
        r = np.random.default_rng(4000 + seed)
        n = int(0.012 * SR)
        out = fft_band(self.noise(n), 1100, 3600, 24, 14) * env(n, 0.6, 1.8)
        return norm(fft_band(out, 320.0, 5500.0, 30, 9)) * r.uniform(0.9, 1.1)

    def mouse_down(self, seed):
        """The ~125 Hz housing layer is the whole difference between a mouse
        button and a fingernail on glass."""
        r = np.random.default_rng(3000 + seed)
        n = int(0.030 * SR)
        click = fft_band(self.noise(n), 1400, 5000) * env(n, 0.2, 2.8)
        t = np.arange(n) / SR
        housing = np.sin(2 * math.pi * 125 * t) * env(n, 0.6, 8.0) * 0.45
        return norm(click + housing) * r.uniform(0.9, 1.1)

    def mouse_up(self):
        n = int(0.026 * SR)
        return norm(fft_band(self.noise(n), 1800, 5600) * env(n, 0.2, 2.0))

    def pop(self, bright=False):
        """Pitched, tiny, with an UPWARD bend. The bend is the identity: fixed
        frequency is a notification beep, bent down means failure."""
        f0, f1, bend, tau, dur = (
            (780, 1240, 8.0, 26.0, 0.095) if bright else (520, 840, 10.0, 20.0, 0.080)
        )
        n = int(dur * SR)
        tone = bent_sine(n, f0, f1, bend) * env(n, 1.4, tau)
        air = fft_band(self.noise(n), 3000 if bright else 2500, 7000 if bright else 6000)
        return norm(tone + air * env(n, 0.3, 3.0) * 0.11)

    def detent(self, seed, brightness):
        """One notch of a reel. Short, dry, metallic — dense trains of these
        must read as a mechanism, not static."""
        r = np.random.default_rng(7000 + seed)
        n = int(0.009 * SR)
        body = fft_band(self.noise(n), 1900 * brightness, 5200 * brightness, 12, 12)
        body = body * env(n, 0.1, 1.5)
        t = np.arange(n) / SR
        ping = np.sin(2 * math.pi * 3100 * brightness * t) * env(n, 0.1, 0.9) * 0.35
        return norm(body + ping) * r.uniform(0.7, 1.0)

    def swish(self):
        out = sweep_noise(0.240, 500, 2400, 16, 1.6, rng=self.rng)
        t = np.linspace(0, 1, out.size)
        return norm(out * np.exp(-(((t - 0.45) / 0.28) ** 2)))

    def whoosh(self):
        out = sweep_noise(0.700, 160, 1500, 32, 1.9, arc=True, rng=self.rng)
        t = np.linspace(0, 1, out.size)
        out = out * np.exp(-(((t - 0.50) / 0.30) ** 2))
        tail = int(0.120 * SR)
        out[-tail:] *= np.linspace(1.0, 0.5, tail)
        return norm(out)

    def sub(self):
        n = int(0.400 * SR)
        return norm(bent_sine(n, 132, 42, 60.0) * env(n, 1.0, 90.0))

    def chime(self):
        """Staggered decays are what make it a chime rather than a chord. No
        reverb — the 1.6s decay IS the space, and a tail here is the fastest
        way to sound like a game level-up."""
        n = int(1.800 * SR)
        t = np.arange(n) / SR
        out = (1.00 * np.sin(2 * math.pi * 587.33 * t) * np.exp(-t / 1.60)
               + 0.50 * np.sin(2 * math.pi * 880.00 * t) * np.exp(-t / 1.10)
               + 0.22 * np.sin(2 * math.pi * 1174.66 * 1.00087 * t) * np.exp(-t / 0.70))
        a = int(0.004 * SR)
        out[:a] *= np.linspace(0, 1, a)
        sp = int(0.250 * SR)
        out[:sp] += fft_band(self.noise(sp), 4000, 9000) * env(sp, 0.3, 60.0) * 0.05
        return norm(out)


# --- reel index -------------------------------------------------------------

# hold, step, hold, step, hold, spin — as fractions of the reel duration.
# A single ease-in-out is already moving when the film starts, so neither of
# the first two items is ever readable. Mirror this in the visual component.
_STAGES = [(0.0, 0, None), (0.228, 0, None), (0.29, 1, "step"),
           (0.414, 1, None), (0.476, 2, "step"), (0.517, 2, None),
           (1.0, -1, "reel")]


def reel_index(frame, start, end, count, ease, staged=True):
    p = (frame - start) / (end - start)
    p = min(max(p, 0.0), 1.0)
    if not staged:
        return bezier_y(p, *ease) * (count - 1)
    if p <= 0:
        return 0.0
    if p >= 1:
        return float(count - 1)
    for i in range(1, len(_STAGES)):
        a_at, a_idx, _ = _STAGES[i - 1]
        b_at, b_idx, kind = _STAGES[i]
        if p > b_at:
            continue
        ia = count - 1 if a_idx < 0 else a_idx
        ib = count - 1 if b_idx < 0 else b_idx
        if ia == ib:
            return float(ia)
        lp = (p - a_at) / (b_at - a_at)
        if kind == "reel":
            lp = bezier_y(lp, *ease)
        elif kind == "step":
            lp = bezier_y(lp, 0.4, 0.0, 0.2, 1.0)
        return ia + (ib - ia) * lp
    return float(count - 1)


# --- assembly ---------------------------------------------------------------

class Track:
    def __init__(self, fps, duration_frames, seed=20260728):
        self.fps = fps
        self.n = int(SR * duration_frames / fps)
        self.left = np.zeros(self.n)
        self.right = np.zeros(self.n)
        self.rng = np.random.default_rng(seed)
        self.kit = Kit(self.rng)

    def place(self, mono, at_frame, gain=1.0, pan=0.0):
        i = int(at_frame / self.fps * SR)
        if i < 0 or i >= self.n or mono.size == 0:
            return
        seg = mono[: self.n - i] * gain
        m = seg.size
        th = (pan + 1.0) * math.pi / 4.0
        self.left[i:i + m] += seg * math.cos(th) * 1.4142
        self.right[i:i + m] += seg * math.sin(th) * 1.4142

    # -- events --

    def typing(self, ev):
        """Audible strokes are DECOUPLED from rendered characters.

        A hero line often types at 25-30 chars/sec because it has to fill the
        shot. Nobody types that; one click per character is a zipper. Strokes
        come from a humanised rhythm instead — mean 128ms, sigma 26ms, floor
        70ms — landing roughly one per four characters."""
        r = np.random.default_rng(ev.get("seed", 11))
        text = ev.get("text", "")
        start_s, end_s = ev["from"] / self.fps, ev["to"] / self.fps
        span = end_s - start_s
        if span <= 0:
            return
        times, t = [], start_s
        while t < end_s:
            times.append(t)
            t += max(0.070, r.normal(0.128, 0.026))
        # A perfectly even train reads as a machine even at the right rate.
        if len(times) > 6:
            for k in range(int(len(times) * 0.55), len(times)):
                times[k] += 0.26
        for i, tt in enumerate(times):
            if tt >= end_s + 0.3:
                break
            idx = int(len(text) * (tt - start_s) / span) if text else 0
            heavy = (0 <= idx < len(text) and text[idx] == " ") or r.random() < 0.12
            g = ev.get("gain", 0.30) * (1.12 if heavy else 1.0)
            self.place(self.kit.key_down(i, heavy), tt * self.fps, g,
                       r.uniform(-0.12, 0.12))
            nxt = (times[i + 1] - tt) if i + 1 < len(times) else 1.0
            if r.random() < 0.45 and nxt > 0.040:
                self.place(self.kit.key_up(i),
                           (tt + r.uniform(0.060, 0.095)) * self.fps, g * 0.20)

    def click(self, ev):
        """Fires ~35ms BEFORE the UI reacts — the ear expects cause to precede
        effect, and a click on the state change reads as late."""
        at = ev["at"] - 0.035 * self.fps
        g = ev.get("gain", 0.50)
        seed = ev.get("seed", int(ev["at"]) % 997)
        self.place(self.kit.mouse_down(seed), at, g)
        self.place(self.kit.mouse_up(), at + 0.042 * self.fps, g * 0.40)

    def reel(self, ev):
        """One detent per slot crossing the centre, rate-limited.

        At peak a reel crosses ~0.8 slots/frame, which unlimited is ~70
        detents/second — past where the ear resolves them, so it turns to
        static. Survivors get brighter and louder with velocity, so it still
        reads as a mechanism spinning up."""
        start, end = int(ev["from"]), int(ev["to"])
        count = int(ev["count"])
        ease = ev.get("ease", [0.72, 0, 0.4, 1])
        staged = ev.get("staged", True)
        min_gap = ev.get("min_gap_s", 0.024)
        last_t, prev, k = -1.0, reel_index(start, start, end, count, ease, staged), 0
        for frame in range(start, end + 1):
            idx = reel_index(frame, start, end, count, ease, staged)
            for slot in range(int(math.floor(prev)) + 1, int(math.floor(idx)) + 1):
                span = idx - prev
                frac = (slot - prev) / span if span > 1e-9 else 0.0
                t = (frame - 1 + frac) / self.fps
                if t - last_t < min_gap:
                    continue
                v = min(1.0, span / 1.2)
                self.place(self.kit.detent(k, 0.9 + 0.35 * v), t * self.fps,
                           0.20 + 0.55 * v, self.rng.uniform(-0.18, 0.18))
                last_t, k = t, k + 1
            prev = idx

    def simple(self, ev):
        kind = ev["type"]
        g = ev.get("gain")
        if kind == "pop":
            self.place(self.kit.pop(ev.get("bright", False)), ev["at"], g or 0.30)
        elif kind == "swish":
            pan = ev.get("pan", [0.0, 0.0])
            self.place(self.kit.swish(), ev["at"], g or 0.36, pan[0])
        elif kind == "whoosh":
            # The arc's peak must land ON the cut; the pre-roll is what makes
            # a hard cut feel intentional rather than abrupt.
            self.place(self.kit.whoosh(), ev["at"] - 0.35 * self.fps, g or 0.9)
            self.place(self.kit.sub(), ev["at"], (g or 0.9) * 0.85)
        elif kind == "chime":
            self.place(self.kit.chime(), ev["at"], g or 0.62)
            self.place(self.kit.sub(), ev["at"] + 0.5, (g or 0.62) * 0.35)

    def write(self, path, peak=0.62):
        stereo = np.stack([self.left, self.right], axis=1)
        # Nothing above 14 kHz (top-end sizzle is most of what makes UI audio
        # sound cheap) and nothing below 32 Hz.
        for ch in range(2):
            stereo[:, ch] = fft_band(stereo[:, ch], 32.0, 14000.0, 12, 12)
        pk = float(np.max(np.abs(stereo)))
        if pk > 0:
            stereo *= peak / pk
        pcm = (np.clip(stereo, -1, 1) * 32767.0).astype("<i2")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        rms = float(np.sqrt(np.mean(stereo ** 2)))
        return pk, rms


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    spec = json.loads(Path(sys.argv[1]).read_text())
    out = sys.argv[2]

    track = Track(spec.get("fps", 60), spec["duration_frames"],
                  spec.get("seed", 20260728))
    for ev in spec["events"]:
        kind = ev["type"]
        if kind == "typing":
            track.typing(ev)
        elif kind == "click":
            track.click(ev)
        elif kind == "reel":
            track.reel(ev)
        else:
            track.simple(ev)

    pk, rms = track.write(out, spec.get("peak", 0.62))
    dur = spec["duration_frames"] / spec.get("fps", 60)
    print(f"wrote {out}")
    print(f"  {dur:.2f}s, {SR} Hz stereo, {len(spec['events'])} events")
    print(f"  pre-normalise peak {pk:.2f}, final peak {spec.get('peak', 0.62)}, "
          f"RMS {rms:.4f} ({20 * math.log10(rms + 1e-12):.1f} dBFS)")


if __name__ == "__main__":
    main()
