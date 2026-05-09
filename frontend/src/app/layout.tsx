// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "../components/Sidebar";
import TopHeader from "../components/TopHeader";
import AuthProvider from "../components/AuthProvider";

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
        <AuthProvider>
          <Sidebar />
          <main className="flex-1 overflow-y-auto h-screen relative flex flex-col">
            <TopHeader />
            <div className="flex-1">
              {children}
            </div>
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}