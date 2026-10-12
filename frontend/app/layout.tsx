import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ServerStatusBanner } from "@/components/ServerStatusBanner";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Resume Customizer",
  description: "Tailor your resume to any job description with evidence-backed scores, India-first.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <ServerStatusBanner />
        {children}
        <Toaster richColors position="top-center" />
      </body>
    </html>
  );
}
