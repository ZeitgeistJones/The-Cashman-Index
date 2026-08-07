"use client";

type Props = {
  label: string;
  help: string;
  numeric?: boolean;
  active?: boolean;
  direction?: "asc" | "desc";
  onSort?: () => void;
  /** Non-sortable header (still shows tooltip). */
  static?: boolean;
};

/** Table header with hover/long-press tooltip (`title`) and help cursor. */
export default function TipTh({
  label,
  help,
  numeric,
  active = false,
  direction = "asc",
  onSort,
  static: isStatic = false,
}: Props) {
  const className = [numeric ? "num" : undefined, "tip-th"]
    .filter(Boolean)
    .join(" ");

  if (isStatic || !onSort) {
    return (
      <th className={className || undefined} title={help}>
        <span className="th-label">{label}</span>
      </th>
    );
  }

  return (
    <th
      className={className || undefined}
      title={help}
      aria-sort={
        active ? (direction === "asc" ? "ascending" : "descending") : "none"
      }
    >
      <button type="button" onClick={onSort} title={help}>
        {label}
        <span className="arrow" aria-hidden="true">
          {active ? (direction === "asc" ? "▲" : "▼") : "↕"}
        </span>
      </button>
    </th>
  );
}
