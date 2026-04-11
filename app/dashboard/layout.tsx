"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { isTokenValid, getStoredUser, logout } from "@/lib/api";
import { getLang, translations, type Lang } from "@/lib/i18n";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const [lang, setLangState] = useState<Lang>("zh");

  useEffect(() => {
    if (!isTokenValid()) { router.push("/login"); return; }
    setUser(getStoredUser());
    setLangState(getLang());

    const handler = () => setLangState(getLang());
    window.addEventListener("pixel_lang_change", handler);
    return () => window.removeEventListener("pixel_lang_change", handler);
  }, [router]);

  if (!user) return null;

  const tr = translations[lang];

  const LINKS = [
    { href: "/dashboard", label: tr.overview, icon: "🏠" },
    { href: "/dashboard/memory", label: tr.memory, icon: "🧠" },
    { href: "/dashboard/notes", label: tr.notes, icon: "📝" },
    { href: "/dashboard/devices", label: tr.devices, icon: "📡" },
    { href: "/dashboard/settings", label: tr.settings, icon: "⚙️" },
  ];

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      {/* Sidebar */}
      <aside className="hidden w-52 shrink-0 border-r bg-muted/20 md:flex md:flex-col">
        <div className="p-4">
          <p className="text-sm font-semibold">{user.name}</p>
          <p className="text-xs text-muted-foreground">{user.email}</p>
        </div>
        <nav className="flex-1 space-y-1 px-2">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
                pathname === l.href
                  ? "bg-primary/10 font-medium text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <span>{l.icon}</span>
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="p-4">
          <button
            onClick={() => { logout(); router.push("/"); }}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            {tr.signOut}
          </button>
        </div>
      </aside>

      {/* Mobile nav */}
      <div className="fixed bottom-0 left-0 right-0 z-50 flex border-t bg-background md:hidden">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`flex flex-1 flex-col items-center py-2 text-xs ${
              pathname === l.href ? "text-foreground" : "text-muted-foreground"
            }`}
          >
            <span className="text-lg">{l.icon}</span>
            <span className="mt-0.5">{l.label}</span>
          </Link>
        ))}
      </div>

      <main className="flex-1 p-6 pb-20 md:pb-6">{children}</main>
    </div>
  );
}
