import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BlindCreators B2B",
  description: "Enterprise SaaS Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning >
        {children}
      </body>
    </html>
  );
}