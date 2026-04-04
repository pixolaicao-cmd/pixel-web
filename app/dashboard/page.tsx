"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getStoredUser, getConversations, getNotes, getMemories } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState({ conversations: 0, notes: 0, memories: 0 });
  const user = getStoredUser();

  useEffect(() => {
    async function loadStats() {
      try {
        const [conv, notes, mem] = await Promise.all([
          getConversations(500),
          getNotes(500),
          getMemories(500),
        ]);
        setStats({
          conversations: conv.messages?.length || 0,
          notes: notes.notes?.length || 0,
          memories: mem.memories?.length || 0,
        });
      } catch { /* ignore */ }
    }
    loadStats();
  }, []);

  const cards = [
    { label: "Conversations", value: stats.conversations, href: "/dashboard/conversations", icon: "\uD83D\uDCAC" },
    { label: "Notes", value: stats.notes, href: "/dashboard/notes", icon: "\uD83D\uDCDD" },
    { label: "Memories", value: stats.memories, href: "/dashboard/memories", icon: "\uD83E\uDDE0" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold">
        Hello, {user?.name || "there"}!
      </h1>
      <p className="mt-1 text-muted-foreground">Here&apos;s your Pixel overview.</p>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {cards.map((c) => (
          <Link
            key={c.label}
            href={c.href}
            className="rounded-xl border bg-card p-6 shadow-sm transition hover:shadow-md"
          >
            <span className="text-3xl">{c.icon}</span>
            <p className="mt-3 text-2xl font-bold">{c.value}</p>
            <p className="text-sm text-muted-foreground">{c.label}</p>
          </Link>
        ))}
      </div>

      <div className="mt-8 rounded-xl border bg-card p-6">
        <h2 className="font-semibold">Quick actions</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link href="/dashboard/soul" className="rounded-lg bg-muted px-4 py-2 text-sm hover:bg-muted/80">
            Customize Pixel Soul
          </Link>
          <Link href="/dashboard/memories" className="rounded-lg bg-muted px-4 py-2 text-sm hover:bg-muted/80">
            View Memories
          </Link>
          <Link href="/dashboard/notes" className="rounded-lg bg-muted px-4 py-2 text-sm hover:bg-muted/80">
            Browse Notes
          </Link>
        </div>
      </div>
    </div>
  );
}
