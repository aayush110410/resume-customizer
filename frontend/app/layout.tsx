import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import { ServerStatusBanner } from "@/components/ServerStatusBanner";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const outfit = Outfit({ variable: "--font-outfit", subsets: ["latin"], weight: ["300", "400", "500", "600", "700"] });

export const metadata: Metadata = {
  title: "Shortlist · Resume Customizer",
  description: "Tailor your resume to any job description with evidence-backed scores, India-first.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${outfit.variable} dark h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <ServerStatusBanner />
        {children}
        <Toaster richColors position="top-center" />
      </body>
    </html>
  );
}
