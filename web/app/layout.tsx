import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";
import NavBar from "@/components/NavBar";

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "TermTypo — Terminal Typing Test",
  description:
    "Terminal-themed multiplayer typing test. Solo practice, ranked matches, private rooms. pip install termtypo or play here.",
  keywords: ["typing test", "terminal", "multiplayer", "monkeytype"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={mono.variable}>
      <body className="min-h-screen bg-[#1a1b26] text-[#c0caf5] font-mono">
        <NavBar />
        <main>{children}</main>
      </body>
    </html>
  );
}
