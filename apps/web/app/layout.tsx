import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RSU Dashboard Hub",
  description: "Tableau de bord hebdomadaire de suivi RSU",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
