"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { isLoggedIn, getStoredUser, logout } from "@/lib/api";

const SIDEBAR_LINKS = [
  { href: "/dashboard", label: "Overview", icon: "\uD83C\uDFE0" },
  { href: "/dashboard/memory", label: "记忆区", icon: "\uD83E\uDDE0" },
  { href: "/dashboard/notes", label: "Notes", icon: "\uD83D\uDCDD" },
  { href: "/dashboard/settings", label: "Settings", icon: "\u2699\uFE0F" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }
    setUser(getStoredUser());
  }, [router]);

  if (!user) return null;

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      {/* Sidebar */}
      <aside className="hidden w-56 shrink-0 border-r bg-muted/20 md:block">
        <div className="p-4">
          <p className="text-sm font-semibold">{user.name}</p>
          <p className="text-xs text-muted-foreground">{user.email}</p>
        </div>
        <nav className="space-y-1 px-2">
          {SIDEBAR_LINKS.map((l) => (
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
        <div className="mt-auto p-4">
          <button
            onClick={() => { logout(); router.push("/"); }}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile nav */}
      <div className="fixed bottom-0 left-0 right-0 z-50 flex border-t bg-background md:hidden">
        {SIDEBAR_LINKS.slice(0, 5).map((l) => (
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

      {/* Content */}
      <main className="flex-1 p-6 pb-20 md:pb-6">{children}</main>
    </div>
  );
}
