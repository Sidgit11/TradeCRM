import type { Metadata } from "next";
import { Anek_Latin, Manrope } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";

const anekLatin = Anek_Latin({
  variable: "--font-heading",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const manrope = Manrope({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "TradeCRM",
  description: "AI-powered multi-channel outreach for commodity traders",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${anekLatin.variable} ${manrope.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-[family-name:var(--font-body)]">
        {children}
        <Toaster
          position="bottom-right"
          toastOptions={{
            className: "font-[family-name:var(--font-body)]",
          }}
        />
      </body>
    </html>
  );
}
