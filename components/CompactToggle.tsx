"use client";

import { useEffect, useState } from "react";

/** Desktop Compact ON by default (null → dense 0.85 zoom). Separate mobile key. */
export const FOI_COMPACT_DESKTOP = "foi-compact";
export const FOI_COMPACT_MOBILE = "foi-compact-mobile";

function isNarrowViewport(): boolean {
  return window.matchMedia("(max-width: 1023px)").matches;
}

export function loadCompactPreference(): boolean {
  if (typeof window === "undefined") return true;
  if (isNarrowViewport()) {
    return localStorage.getItem(FOI_COMPACT_MOBILE) === "1";
  }
  // Desktop: Compact ON unless explicitly "0"
  return localStorage.getItem(FOI_COMPACT_DESKTOP) !== "0";
}

function saveCompactPreference(on: boolean) {
  if (isNarrowViewport()) {
    localStorage.setItem(FOI_COMPACT_MOBILE, on ? "1" : "0");
  } else {
    localStorage.setItem(FOI_COMPACT_DESKTOP, on ? "1" : "0");
  }
}

/** Pill toggle: Compact = global body zoom 0.85 on desktop; off = comfort-view at 100%. */
export default function CompactToggle() {
  const [compact, setCompact] = useState(true);

  useEffect(() => {
    setCompact(loadCompactPreference());
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("comfort-view", !compact);
  }, [compact]);

  function toggle() {
    const next = !compact;
    saveCompactPreference(next);
    setCompact(next);
  }

  return (
    <button
      type="button"
      className={`compact-toggle${compact ? " active" : ""}`}
      onClick={toggle}
      title={
        compact
          ? "Comfortable size (100% zoom)"
          : "Compact density (fit more on screen)"
      }
      aria-pressed={compact}
    >
      {compact ? "Compact ✓" : "Compact"}
    </button>
  );
}
