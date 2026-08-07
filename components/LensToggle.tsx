"use client";

import { LENS_ORDER, LENSES, type LensId } from "@/lib/lenses";

const OVERLAP_HINT =
  "Titles, pennants, depth, and win% overlap (~0.41 of Balanced) — lenses usually move ranks only a few places.";

export default function LensToggle({
  value,
  onChange,
}: {
  value: LensId;
  onChange: (id: LensId) => void;
}) {
  const active = LENSES[value];
  return (
    <div className="lens-pills">
      <span className="lens-pills-label" id="lens-pills-label">
        Lens
      </span>
      <div
        className="lens-pill-group"
        role="group"
        aria-labelledby="lens-pills-label"
      >
        {LENS_ORDER.map((id) => (
          <button
            key={id}
            type="button"
            className={value === id ? "active" : undefined}
            aria-pressed={value === id}
            title={LENSES[id].blurb}
            onClick={() => onChange(id)}
          >
            {LENSES[id].label}
          </button>
        ))}
      </div>
      <p className="lens-pill-blurb" title={OVERLAP_HINT}>
        {active.blurb}
      </p>
    </div>
  );
}
