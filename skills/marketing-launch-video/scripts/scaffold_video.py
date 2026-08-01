#!/usr/bin/env python3
"""
Scaffold a Remotion project for a product launch video.

    python3 scaffold_video.py <target-dir> --name my-launch --fps 60 --seconds 45

Creates a STANDALONE project with its own git repo. Video tooling has heavy
dependencies and a different cadence than the product it advertises — keep it
out of the product's repo unless the user asks otherwise.

The version pins here are the ones that actually work together. Getting them
wrong produces confusing failures rather than clean errors:
  - React 18, because most product UIs are React 18 and importing their
    components into a React 19 project gives duplicate-React hook errors.
  - Tailwind v3 with @remotion/tailwind. (v4 needs @remotion/tailwind-v4 and a
    CSS-first config — check which the product uses and adjust.)

After running: copy the product's theme CSS and Tailwind config in, then fill
in src/timeline.ts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"


def w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--name", default="product-launch")
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--seconds", type=float, default=45.0)
    ap.add_argument("--bpm", type=int, default=120,
                    help="Beat should be a whole number of frames: at 60fps, "
                         "120 BPM = 30 frames, 90 = 40, 150 = 24.")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--shape", choices=("narrative", "chapters"),
                    default="narrative",
                    help="narrative = one user, one job, one artifact (default). "
                         "chapters = three labelled features, for gated products "
                         "or genuinely separate capabilities.")
    ap.add_argument("--mood", default="minimal",
                    choices=("energetic", "soft", "cinematic", "minimal",
                             "warm", "tense"),
                    help="Seeds music.spec.json. ASK the user first — many "
                         "have their own track.")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()

    root = Path(a.target).expanduser().resolve()
    frames = int(round(a.seconds * a.fps))
    beat = a.fps * 60 // a.bpm
    if a.fps * 60 % a.bpm:
        print(f"! {a.bpm} BPM is not a whole number of frames at {a.fps}fps "
              f"(beat = {a.fps*60/a.bpm:.2f}). Cuts will drift off the beat.")

    for d in ("src/components", "src/scenes", "src/hooks", "src/data",
              "src/styles", "public", "scripts", "out"):
        (root / d).mkdir(parents=True, exist_ok=True)

    w(root / "package.json", json.dumps({
        "name": a.name, "private": True, "version": "0.1.0",
        "scripts": {
            "studio": "remotion studio",
            "still": "remotion still",
            "render": f"remotion render Main out/{a.name}.mp4 --concurrency=4",
        },
        "dependencies": {
            "@remotion/cli": "^4.0.0",
            "@remotion/tailwind": "^4.0.0",
            "clsx": "^2.1.1",
            "lucide-react": "^0.468.0",
            "react": "18.3.1",
            "react-dom": "18.3.1",
            "remotion": "^4.0.0",
            "tailwind-merge": "^2.6.0",
        },
        "devDependencies": {
            "@types/react": "^18.3.18",
            "@types/react-dom": "^18.3.5",
            "autoprefixer": "^10.4.20",
            "postcss": "^8.4.49",
            "tailwindcss": "^3.4.17",
            "tailwindcss-animate": "^1.0.7",
            "typescript": "^5.7.2",
        },
    }, indent=2) + "\n")

    w(root / "remotion.config.ts", f"""
import path from "node:path";
import {{ Config }} from "@remotion/cli/config";
import {{ enableTailwind }} from "@remotion/tailwind";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// Remotion spawns a Chrome tab per slot. The default (core count) swaps on
// 16GB and gets slower, not faster.
Config.setConcurrency(4);

Config.overrideWebpackConfig((current) => {{
  const c = enableTailwind(current);
  return {{
    ...c,
    resolve: {{
      ...c.resolve,
      // Remotion bundles with webpack and never reads vite.config.ts, so any
      // path alias the product uses has to be re-declared here.
      alias: {{ ...c.resolve?.alias, "@": path.join(process.cwd(), "src") }},
    }},
  }};
}});
""")

    w(root / "tsconfig.json", json.dumps({
        "compilerOptions": {
            "target": "ES2022", "lib": ["ES2022", "DOM", "DOM.Iterable"],
            "module": "ESNext", "moduleResolution": "bundler", "jsx": "react-jsx",
            "strict": True, "skipLibCheck": True, "esModuleInterop": True,
            "resolveJsonModule": True, "isolatedModules": True, "noEmit": True,
            "baseUrl": ".", "paths": {"@/*": ["./src/*"]},
        },
        "include": ["src", "remotion.config.ts", "tailwind.config.ts"],
    }, indent=2) + "\n")

    w(root / "postcss.config.js",
      "module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };\n")

    w(root / "tailwind.config.ts", """
import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/*
 * Vendor the PRODUCT's theme here — colours, radii, shadows, fonts.
 *
 * Deliberately do NOT copy its `animation` / `keyframes` blocks. Those are
 * wall-clock driven and freeze at frame 0 in a render; leaving them in invites
 * a component to silently use one. Re-express motion against useCurrentFrame()
 * instead.
 *
 * If the product's colours are CSS custom properties (hsl(var(--primary))),
 * you must also bring its :root block into src/styles/globals.css or every
 * component renders colourless.
 */
export default {
  darkMode: ["class"],
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [animate],
} satisfies Config;
""")

    w(root / "src/styles/globals.css", """
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Paste the product's :root (and .dark) custom properties here. */
@layer base {
  :root {
    /* --background: ...; --foreground: ...; --primary: ...; */
  }
  html, body { margin: 0; padding: 0; -webkit-font-smoothing: antialiased; }
}
""")

    # Lay the shots out across however many bars the requested duration
    # actually gives, rather than a fixed table that leaves the tail empty.
    bar = beat * 4
    total_bars = max(6, frames // bar)

    if a.shape == "chapters":
        weights = [("hook", 2), ("chapter1", 3), ("chapter2", 3),
                   ("chapter3", 3), ("slate", 2)]
    else:
        weights = [("hook", 2), ("ask", 3), ("work", 4),
                   ("artifact", 4), ("control", 3), ("slate", 2)]

    unit = sum(w for _, w in weights)
    bars, used = [], 0
    for i, (name, wgt) in enumerate(weights):
        b = (total_bars - used if i == len(weights) - 1
             else max(1, round(wgt / unit * total_bars)))
        bars.append((name, b))
        used += b

    lines, at = [], 0
    # The card is 9 beats (~4.5s at 120 BPM) — long enough to read a heading
    # and a one-line summary, short enough not to stall the film. See
    # references/structure.md.
    CARD = 9
    for name, b in bars:
        if a.shape == "chapters" and name.startswith("chapter"):
            n = name[-1]
            lines.append((f"card{n}", f"BAR * {at}", f"BEAT * {CARD}"))
            lines.append((f"feature{n}", f"BAR * {at} + BEAT * {CARD}",
                          f"BAR * {b} - BEAT * {CARD}"))
        else:
            # The last shot absorbs any frames left over by the bar rounding,
            # so the film never ends on a second of nothing.
            dur = (f"DURATION - BAR * {at}" if name == weights[-1][0]
                   else f"BAR * {b}")
            lines.append((name, f"BAR * {at}" if at else "0", dur))
        at += b

    kw = max(len(n) for n, _, _ in lines) + 1
    fw = max(len(f) for _, f, _ in lines) + 1
    shots = "".join(
        f"  {(n + ':').ljust(kw)} {{ from: {(f + ',').ljust(fw)} "
        f"duration: {d} }},\n" for n, f, d in lines)

    # Music sections land on the same frames as the shots above.
    section_at = {n: at_ * bar for (n, at_) in
                  zip([n for n, _ in bars],
                      [sum(b for _, b in bars[:i]) for i in range(len(bars))])}

    w(root / "src/timeline.ts", f"""
/**
 * Frame math and shot boundaries.
 *
 * {a.fps} fps, {a.bpm} BPM -> beat = {beat} frames, bar = {beat*4} frames.
 * Put every shot boundary on a beat. Even with no music this gives the cut an
 * internal rhythm, and it means a bed can be added later without re-editing.
 *
 * Total = {frames} frames = {a.seconds:.1f}s.
 */

export const FPS = {a.fps};
export const WIDTH = {a.width};
export const HEIGHT = {a.height};

export const BPM = {a.bpm};
export const BEAT = {beat};
export const BAR = BEAT * 4;
export const DURATION = {frames};

/** Shot boundaries. Keep each `from` on a multiple of BEAT. */
export const SHOTS = {{
{shots}}} as const;
""")

    w(root / "src/Root.tsx", f"""
import React from "react";
import {{ Composition }} from "remotion";

import {{ Main }} from "@/Main";
import {{ DURATION, FPS, HEIGHT, WIDTH }} from "@/timeline";

import "@/styles/globals.css";

export function RemotionRoot() {{
  return (
    <>
      <Composition
        id="Main"
        component={{Main}}
        durationInFrames={{DURATION}}
        fps={{FPS}}
        width={{WIDTH}}
        height={{HEIGHT}}
      />
      {{/* Silent variant so stills render before the audio file exists. */}}
      <Composition
        id="MainSilent"
        component={{Main}}
        durationInFrames={{DURATION}}
        fps={{FPS}}
        width={{WIDTH}}
        height={{HEIGHT}}
        defaultProps={{{{ withAudio: false }}}}
      />
    </>
  );
}}
""")

    w(root / "src/Main.tsx", """
import React from "react";
import { AbsoluteFill, Audio, continueRender, delayRender, staticFile } from "remotion";

/**
 * Hold frame 0 until the webfonts are rasterised, or the opening frames
 * render in the fallback face and the weight visibly swaps mid-shot.
 *
 * This MUST live inside a component. delayRender() at module scope runs during
 * bundle evaluation, before there is a render scope — stills still work, and
 * then `remotion render` fails with a stack pointing at the import.
 */
function useFontsReady() {
  const [handle] = React.useState(() => delayRender("fonts"));
  React.useEffect(() => {
    let cancelled = false;
    document.fonts.ready.then(() => {
      if (!cancelled) continueRender(handle);
    });
    return () => {
      cancelled = true;
    };
  }, [handle]);
}

export function Main({ withAudio = true }: { withAudio?: boolean }) {
  useFontsReady();
  return (
    <AbsoluteFill className="bg-background font-sans">
      {/* Scenes go here, layered: product underneath, title cards on top. */}

      {/* Two tracks, two files, so either can be replaced without
          regenerating the other. Music at peak ~0.30 and effects at ~0.62
          (set when synthesizing); the bed should be quiet enough that you
          notice it only when it stops. */}
      {withAudio ? (
        <>
          <Audio src={staticFile("music.wav")} volume={0.85} />
          <Audio src={staticFile("sfx.wav")} />
        </>
      ) : null}
    </AbsoluteFill>
  );
}
""")

    w(root / "src/index.ts", """
import { registerRoot } from "remotion";
import { RemotionRoot } from "@/Root";

registerRoot(RemotionRoot);
""")

    w(root / "src/lib/utils.ts", """
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
""")

    for src, dst in (("useCamera.ts", "src/hooks/useCamera.ts"),
                     ("ChapterCard.tsx", "src/components/ChapterCard.tsx")):
        if (ASSETS / src).exists():
            shutil.copy(ASSETS / src, root / dst)

    w(root / "sfx.spec.json", json.dumps({
        "fps": a.fps, "duration_frames": frames, "peak": 0.62,
        "_comment": "Three to five events is usually plenty. See references/sound.md.",
        "events": [
            {"type": "typing", "from": beat * 8, "to": beat * 14, "text": "the typed line"},
            {"type": "click", "at": beat * 16},
        ],
    }, indent=2) + "\n")

    # Music arrangement, on the same frames as the shot boundaries above.
    # Layers entering is how the film gains momentum; strip back to pad for
    # the slate.
    if a.shape == "chapters":
        sections = [
            {"at": 0, "name": "intro", "layers": ["pad", "sub"]},
            {"at": section_at["chapter1"], "name": "build",
             "layers": ["pad", "sub", "bass", "pluck"]},
            {"at": section_at["chapter2"], "name": "main",
             "layers": ["pad", "bass", "kick", "hat", "pluck"]},
            {"at": section_at["slate"], "name": "outro",
             "layers": ["pad", "bell"]},
        ]
        hits = [{"at": section_at["chapter1"], "riser": True}]
    else:
        sections = [
            {"at": 0, "name": "intro", "layers": ["pad", "sub"]},
            {"at": section_at["ask"], "name": "build",
             "layers": ["pad", "sub", "bass", "pluck"]},
            {"at": section_at["work"], "name": "main",
             "layers": ["pad", "bass", "kick", "hat", "pluck", "clap"]},
            {"at": section_at["slate"], "name": "outro",
             "layers": ["pad", "bell"]},
        ]
        hits = [{"at": section_at["artifact"], "riser": True}]

    w(root / "music.spec.json", json.dumps({
        "fps": a.fps, "duration_frames": frames, "bpm": a.bpm,
        "mood": a.mood, "peak": 0.30,
        "_comment": "ASK the user before synthesizing — many have their own "
                    "track. Section `at` values are FRAMES and should sit on "
                    "real shot boundaries. See references/music.md.",
        "sections": sections,
        "hits": hits,
        "ducks": [],
    }, indent=2) + "\n")

    w(root / ".gitignore", "node_modules/\nout/\n.remotion/\npublic/*.wav\n*.log\n.DS_Store\n")

    w(root / "README.md", f"""
# {a.name}

Launch video. Standalone — does not modify the product's repo.

```bash
npm install
python3 <skill-dir>/scripts/make_sfx.py   sfx.spec.json   public/sfx.wav
python3 <skill-dir>/scripts/make_music.py music.spec.json public/music.wav
npm run studio          # scrub at localhost:3000
npx remotion still MainSilent out/f0300.png --frame=300   # LOOK at this before rendering
npm run render
```

{a.fps} fps, {a.bpm} BPM (beat = {beat} frames), {frames} frames = {a.seconds:.1f}s.
Shape: **{a.shape}**. Music mood: **{a.mood}**.

The app is laid out at {a.width}x{a.height} whatever the output resolution; the
camera is a transform on that layout. See `src/hooks/useCamera.ts`.

To swap the music for a real track, drop any WAV or MP3 at `public/music.wav`
and re-render. Nothing else changes.
""")

    if not a.no_git and not (root / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=root, check=False)

    print(f"scaffolded {root}")
    print(f"  {a.fps}fps, {a.bpm} BPM (beat={beat}f), {frames} frames "
          f"({a.seconds:.1f}s), shape={a.shape}, mood={a.mood}")
    print("\nnext:")
    print(f"  cd {root} && npm install")
    print("  - vendor the product's tailwind.config + theme CSS")
    print("  - fill in src/timeline.ts and src/data/")
    print("  - ASK whether they have a music track before synthesizing one")
    print("  - render a still and look at it before rendering the film")


if __name__ == "__main__":
    main()
