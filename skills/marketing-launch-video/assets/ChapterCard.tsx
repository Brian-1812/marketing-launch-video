import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

/**
 * A chapter card for the chaptered feature shape — an index, a heading that
 * claims an outcome, and one sentence saying how.
 *
 * It is not a title card. Its job is to be read and then get out of the way,
 * so everything here is tuned for legibility over personality: left-aligned at
 * the same x as the product content that follows, on the film's own
 * background so the transition into the feature can be a push rather than a
 * cut.
 *
 * See references/structure.md for how to write the labels and order the
 * chapters. The short version: name the outcome, not the mechanism; heading
 * 2-5 words; summary under 14 words; steal the product's own copy.
 */

export type Chapter = {
  /** "01", "02", "03" — tells the viewer how much is left, which keeps them watching. */
  index: string;
  /** 2-5 words. An outcome, not a mechanism. */
  heading: string;
  /** One sentence, under 14 words, wrapping to at most two lines. */
  summary: string;
};

type Props = Chapter & {
  /** Absolute frame this card starts on. */
  from: number;
  /** Total frames the card is up. 120-150 at 60fps; under 2s and nobody
   *  finishes the summary, over 3s and the film stalls. */
  duration?: number;
  /** Where the eye should sit — match the product content that follows. */
  x?: number;
  accent?: string;
  fg?: string;
  muted?: string;
  background?: string;
};

const OUT = Easing.bezier(0.16, 1, 0.3, 1);
const IN = Easing.bezier(0.55, 0, 1, 0.45);

export const ChapterCard: React.FC<Props> = ({
  index,
  heading,
  summary,
  from,
  duration = 132,
  x = 220,
  accent = "var(--accent, #ffb020)",
  fg = "var(--foreground, #f5f2e8)",
  muted = "var(--muted-foreground, #8d94a6)",
  background = "var(--background, #0b0d14)",
}) => {
  const frame = useCurrentFrame();
  const t = frame - from;
  if (t < 0 || t >= duration) return null;

  // Type animates with clip-path, opacity and transform ONLY. Animating
  // fontSize or letter-spacing reflows and re-hints the glyphs mid-shot,
  // which shows up as a visible shimmer.
  const rise = (a: number, b: number) =>
    interpolate(t, [a, b], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: OUT,
    });

  const rule = rise(2, 20);
  const num = rise(4, 18);
  const head = rise(8, 26);
  const sum = rise(16, 36);

  // A slow drift over the hold, so a static frame isn't dead.
  const drift = interpolate(t, [0, duration], [1, 1.018]);

  // Leaves upward — pair it with the next scene rising into place on the same
  // curve and the transition reads as turning a page.
  const exitY = interpolate(t, [duration - 14, duration], [0, -26], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: IN,
  });
  const exitO = interpolate(t, [duration - 12, duration], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background, opacity: exitO }}>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          paddingLeft: x,
          paddingRight: 220,
          transform: `translateY(${exitY}px) scale(${drift})`,
          transformOrigin: "0% 50%",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <span
            style={{
              fontSize: 26,
              fontWeight: 600,
              letterSpacing: "0.18em",
              color: accent,
              opacity: num,
            }}
          >
            {index}
          </span>
          <span
            style={{
              display: "block",
              height: 2,
              width: 96 * rule,
              background: accent,
              opacity: 0.55,
            }}
          />
        </div>

        <h2
          style={{
            margin: "28px 0 0",
            fontSize: 80,
            fontWeight: 600,
            lineHeight: 1.05,
            letterSpacing: "-0.032em",
            color: fg,
            opacity: head,
            clipPath: `inset(${(1 - head) * 100}% 0 0 0)`,
          }}
        >
          {heading}
        </h2>

        <p
          style={{
            margin: "22px 0 0",
            maxWidth: 900,
            fontSize: 36,
            fontWeight: 400,
            lineHeight: 1.38,
            letterSpacing: "-0.012em",
            color: muted,
            opacity: sum,
            transform: `translateY(${(1 - sum) * 10}px)`,
          }}
        >
          {summary}
        </p>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
