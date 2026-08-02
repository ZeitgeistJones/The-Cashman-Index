import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Front Office Index",
  description:
    "MLB franchises and GMs ranked on payroll efficiency, draft value, peer trades, and results — same weights for every club, 2006–present.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
