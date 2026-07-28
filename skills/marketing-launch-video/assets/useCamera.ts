import { spring, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Focus-point camera over a fixed layout.
 *
 * The product is laid out at LAYOUT_W x LAYOUT_H whatever the output
 * resolution. A shot is then a point in that layout plus a scale, which is
 * what makes shots tunable: render a still, see what you want centred, read
 * its coordinates, put them here. No guessing at translate values.
 *
 * Copy this into src/hooks/ and set LAYOUT_W / LAYOUT_H to your layout size.
 */

export const LAYOUT_W = 1920;
export const LAYOUT_H = 1080;

export interface Shot {
  /** Point in layout space to centre. */
  cx: number;
  cy: number;
  scale: number;
}

export interface CameraKeyframe extends Shot {
  /** Absolute frame at which the move INTO this shot begins. */
  at: number;
  /** Frames the move takes. It then holds until the next keyframe. */
  duration?: number;
  /**
   * Snap instantly instead of springing. A push-in says "look closer at the
   * same thing"; a cut says "we are somewhere else now".
   */
  cut?: boolean;
}

/** ~1s at 60fps. The camera has mass; this is the one thing that is slow. */
export const CAMERA_MOVE = 60;

/**
 * Clamp the translate so the scaled layout always covers the frame — a shot
 * near an edge slides back in rather than exposing blank canvas.
 *
 * The consequence worth knowing: an element at the bottom of the page can
 * never be vertically centred in a close-up, because that would require
 * showing space below the page. If you need it centred, render the component
 * in isolation instead of cropping the page.
 */
function clampedTranslate(shot: Shot, frameW: number, frameH: number) {
  const { cx, cy, scale } = shot;
  const tx = Math.min(
    0,
    Math.max(frameW - LAYOUT_W * scale, frameW / 2 - cx * scale),
  );
  const ty = Math.min(
    0,
    Math.max(frameH - LAYOUT_H * scale, frameH / 2 - cy * scale),
  );
  return { tx, ty };
}

/**
 * Returns a CSS transform string. Apply it to a div sized LAYOUT_W x LAYOUT_H
 * with transformOrigin "0 0".
 *
 * Keyframes are absolute-frame based and hold between moves — without the
 * hold, a push-in creeps across the whole segment instead of arriving and
 * settling.
 */
export function useCamera(keyframes: CameraKeyframe[]): string {
  const frame = useCurrentFrame();
  const { fps, width: frameW, height: frameH } = useVideoConfig();

  if (keyframes.length === 0) return "none";

  let activeIndex = 0;
  for (let i = 0; i < keyframes.length; i++) {
    if (frame >= keyframes[i].at) activeIndex = i;
  }

  const target = keyframes[activeIndex];
  const origin = keyframes[Math.max(0, activeIndex - 1)];

  const from = clampedTranslate(origin, frameW, frameH);
  const to = clampedTranslate(target, frameW, frameH);

  const progress =
    activeIndex === 0 || target.cut
      ? 1
      : spring({
          frame: frame - target.at,
          fps,
          durationInFrames: target.duration ?? CAMERA_MOVE,
          // Heavily damped: a slow, weighty push with no overshoot. Never
          // linear — a linear camera move is the fastest way to look cheap.
          config: { damping: 200, stiffness: 60, mass: 1 },
        });

  const tx = from.tx + (to.tx - from.tx) * progress;
  const ty = from.ty + (to.ty - from.ty) * progress;
  const scale = origin.scale + (target.scale - origin.scale) * progress;

  return `translate(${tx.toFixed(3)}px, ${ty.toFixed(3)}px) scale(${scale.toFixed(4)})`;
}

/**
 * Starting points. Tune cx/cy from a rendered still.
 *
 * Below ~1.3 type is too small on a phone, which is where most of these are
 * watched. Above ~2.6 you are usually better off isolating the component —
 * see references/camera.md.
 */
export const SHOT_SCALES = {
  establishing: 1.0, // the whole app. Use twice, briefly. Not a default.
  working: 1.45, //     a column of content plus context
  reading: 1.8, //      text you want the viewer to actually read
  detail: 2.3, //       one control, one changed word, one press
} as const;
