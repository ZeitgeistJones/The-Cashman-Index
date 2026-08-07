"use client";

import { LENS_ORDER, LENSES, type LensId } from "@/lib/lenses";

export default function LensToggle({
  value,
  onChange,
}: {
  value: LensId;
  onChange: (id: LensId) => void;
}) {
  const active = LENSES[value];
  return (
    <div className="lens-block">
      <div
        className="filter-row mode-toggle lens-toggle"
        role="group"
        aria-label="Success lens"
      >
        {LENS_ORDER.map((id) => (
          <button
            key={id}
            type="button"
            className={value === id ? "active" : undefined}
            aria-pressed={value === id}
            onClick={() => onChange(id)}
          >
            {LENSES[id].label}
          </button>
        ))}
      </div>
      <p className="section-note lens-blurb">{active.blurb}</p>
    </div>
  );
}
