import type { Metadata } from "next";
import { Instrument_Sans } from "next/font/google";
import "./globals.css";

const instrumentSans = Instrument_Sans({ variable: "--font-instrument-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Sarjy",
  description: "A voice assistant that remembers you",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${instrumentSans.variable} h-full font-sans antialiased`}>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
