// Diamond-on-square mark. Colors follow page tokens so it flips in dark mode.

type BrandMarkProps = {
  size?: number;
};

export default function BrandMark({ size = 32 }: BrandMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      aria-hidden="true"
      className="brand-mark"
    >
      <rect width="32" height="32" rx="7" fill="var(--accent)" />
      <path
        d="M16 7.5 24.5 16 16 24.5 7.5 16Z"
        fill="none"
        stroke="var(--bg)"
        strokeWidth="2.25"
        strokeLinejoin="round"
      />
      <path d="M16 13 19 16 16 19 13 16Z" fill="var(--bg)" />
    </svg>
  );
}
