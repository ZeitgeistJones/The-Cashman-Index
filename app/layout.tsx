import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Cashman Index",
  description:
    "Brian Cashman's Yankees front-office moves, scored with objective baseball math.",
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
