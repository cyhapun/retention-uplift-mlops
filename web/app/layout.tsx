import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RetentionOps Control Center",
  description: "Unified dashboard for RetentionOps MLOps operations.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
