"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getMemories, createMemory, deleteMemory } from "@/lib/api";

interface Memory {
  id: string;
  content: string;
  category: string;
  created_at: string;
}

const CATEGORIES = ["general", "preference", "schedule", "person", "important"];

export default function MemoriesPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("general");
  const [saving, setSaving] = useState(false);

  async function loadMemories() {
    try {
      const data = await getMemories();
      setMemories(data.memories || []);
    } catch { /* empty */ }
  }

  useEffect(() => { loadMemories(); }, []);

  async function handleAdd() {
    if (!newContent.trim()) return;
    setSaving(true);
    try {
      await createMemory(newContent, newCategory);
      setNewContent("");
      await loadMemories();
    } catch { /* empty */ }
    setSaving(false);
  }

  async function handleDelete(id: string) {
    try {
      await deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch { /* empty */ }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Memories</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Things Pixel remembers about you. Add or remove anytime.
      </p>

      {/* Add new */}
      <div className="mt-6 flex gap-2">
        <Input
          placeholder='e.g. "I like oat milk"'
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          className="flex-1"
          onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
        />
        <select
          value={newCategory}
          onChange={(e) => setNewCategory(e.target.value)}
          className="rounded-lg border bg-background px-3 text-sm"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <Button onClick={handleAdd} disabled={saving || !newContent.trim()}>
          {saving ? "..." : "Add"}
        </Button>
      </div>

      {/* List */}
      <div className="mt-6 space-y-2">
        {memories.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No memories yet. Tell Pixel something to remember!
          </p>
        )}
        {memories.map((m) => (
          <div key={m.id} className="flex items-center justify-between rounded-lg border bg-card px-4 py-3">
            <div className="flex-1">
              <p className="text-sm">{m.content}</p>
              <div className="mt-1 flex gap-2">
                <span className="rounded bg-muted px-2 py-0.5 text-xs">{m.category}</span>
                <span className="text-xs text-muted-foreground">
                  {new Date(m.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <button
              onClick={() => handleDelete(m.id)}
              className="ml-4 text-xs text-muted-foreground hover:text-red-500"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
