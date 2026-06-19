import type { Metadata } from "next";
import { Golos_Text, JetBrains_Mono, Oswald } from "next/font/google";
import "uplot/dist/uPlot.min.css";
import "./globals.css";
import { Providers } from "./providers";

// Monaco design system: Oswald (condensed display), Golos Text (body, Cyrillic), JetBrains Mono (data).
const oswald = Oswald({
  variable: "--font-oswald",
  subsets: ["latin", "cyrillic"],
  weight: ["500", "600", "700"],
});
const golos = Golos_Text({ variable: "--font-golos", subsets: ["latin", "cyrillic"] });
const jetbrains = JetBrains_Mono({ variable: "--font-jetbrains", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ApexAI — AI-тренер по симрейсингу",
  description: "AI-разбор твоей телеметрии F1: где ты теряешь секунды, понятно и на русском.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="ru"
      className={`${oswald.variable} ${golos.variable} ${jetbrains.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        {/* Deep red racing glow at the bottom of the page (decorative). */}
        <div
          className="pointer-events-none fixed inset-x-0 bottom-0 z-0 h-[45vh]"
          style={{
            background:
              "radial-gradient(58% 80% at 50% 100%, rgba(255,45,70,0.14), transparent 72%)",
          }}
        />
        <div className="relative z-10">
          <Providers>{children}</Providers>
        </div>
      </body>
    </html>
  );
}
