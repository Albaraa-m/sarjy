import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Sarjy",
  description: "A voice assistant that remembers you",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full font-sans antialiased`}>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
