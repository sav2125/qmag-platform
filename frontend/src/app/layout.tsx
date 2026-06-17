import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Qullamaggie Platform",
  description: "Actionable Qullamaggie trading setups",
};

const NAV = [
  { href: "/",        label: "Dashboard" },
  { href: "/macro",   label: "Macro"     },
  { href: "/analyze", label: "Analyze"   },
  { href: "/setups",  label: "Setups"    },
  { href: "/scoring", label: "Scoring"   },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/settings",  label: "Settings"  },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-50 min-h-screen`}>
        <nav className="bg-indigo-950 text-white px-6 py-3 flex items-center gap-8 shadow-lg">
          <span className="font-bold text-lg tracking-tight">📈 Qullamaggie</span>
          <div className="flex gap-6">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href}
                className="text-sm text-indigo-200 hover:text-white transition-colors">
                {n.label}
              </Link>
            ))}
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
