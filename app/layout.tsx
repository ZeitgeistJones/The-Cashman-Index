import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Front Office Index",
  description:
    "MLB franchises and GMs ranked on payroll efficiency, draft value, peer trades, and results — same weights for every club, 2006–present.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0e1116" },
  ],
};

/**
 * Tripwire-style density: one global body zoom on desktop, toggled via
 * html.comfort-view. Must run before paint (same idea as theme FOUC guards).
 * Desktop key foi-compact (null = Compact ON). Mobile key foi-compact-mobile
 * (null = comfort; Compact is opt-in). Never stack a second zoom on tables.
 */
const DENSITY_BOOT = `(function(){try{var n=window.matchMedia("(max-width:1023px)").matches;if(n){if(localStorage.getItem("foi-compact-mobile")!=="1")document.documentElement.classList.add("comfort-view")}else{if(localStorage.getItem("foi-compact")==="0")document.documentElement.classList.add("comfort-view")}}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: DENSITY_BOOT }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
