import type { Easing, Transition } from "framer-motion";

const easeOut: Easing = [0.16, 1, 0.3, 1];
const easeInOut: Easing = [0.65, 0, 0.35, 1];
const spring: Transition = { type: "spring", stiffness: 350, damping: 30 };

export const motion = {
  duration: {
    fast: 0.15,
    medium: 0.25,
    slow: 0.4,
  },
  ease: {
    out: easeOut,
    inOut: easeInOut,
    spring,
  },
} as const;

export const easings = {
  out: easeOut,
  inOut: easeInOut,
} as const;
