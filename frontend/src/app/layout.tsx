// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import Sidebar from "../components/Sidebar";
import TopHeader from "../components/TopHeader";
import "./globals.css";

export const metadata: Metadata = {
  title: "BlindCreators SaaS",
  description: "Enterprise YouTube Analytics & AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning className="antialiased flex min-h-screen bg-slate-900 text-slate-50">

        {/* Global Sidebar Component */}
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto h-screen relative flex flex-col">

          {/* Top Header Component */}
          <TopHeader />

          {/* Page Content (Dashboard, AI Tools, etc.) */}
          <div className="flex-1">
            {children}
          </div>

        </main>

      </body>
    </html>
  );
}