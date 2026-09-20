/**
 * Chart color tokens. Values are taken verbatim from the dataviz skill's
 * validated reference palette (references/palette.md) - never eyeballed.
 *
 * - STATUS colors are reserved for state (good/warning/critical) and always
 *   paired with an icon/label/legend, never color alone.
 * - CATEGORICAL slots are for identity when two or more series are *not*
 *   states (e.g. "average" vs "p95" latency) - assigned in fixed order.
 *
 * Verified: `node validate_palette.js "#2a78d6,#eb6834" --mode light` -> all
 * checks PASS (lightness, chroma, CVD separation, normal-vision floor, contrast).
 */

export const STATUS = {
  good: "#0ca30c", // approved / upheld / success
  warning: "#fab219", // pended / overridden - amber, needs icon+label per skill (sub-3:1 on light)
  critical: "#d03b3b", // denied / error
} as const;

// Categorical slots 1 and 2 from the default 8-hue order, used only for
// non-status series comparisons (e.g. avg vs p95 latency).
export const CATEGORICAL = {
  slot1: "#2a78d6", // blue
  slot2: "#eb6834", // orange
} as const;

export const CHART_INK = {
  primary: "#0b0b0b",
  secondary: "#52514e",
  muted: "#898781",
  gridline: "#e1e0d9",
  surface: "#ffffff",
} as const;

export const DETERMINATION_COLORS: Record<string, string> = {
  approved: STATUS.good,
  denied: STATUS.critical,
  pended: STATUS.warning,
};

export const REVIEW_DECISION_COLORS: Record<string, string> = {
  upheld: STATUS.good,
  overridden: STATUS.warning,
};
