"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getConversations, getMemories, createMemory, deleteMemory } from "@/lib/api";

type Tab = "conversations" | "memories";

interface Message {
  id?: string;
  role: "user" | "pixel";
  content: string;
  created_at?: string;
}

interface Memory {
  id: string;
  content: string;
  category: string;
  created_at: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  general: "通用",
  preference: "偏好",
  schedule: "日程",
  person: "人物",
  important: "重要",
};

export default function MemoryPage() {
  const [tab, setTab] = useState<Tab>("conversations");

  // Conversations
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Memories
  const [memories, setMemories] = useState<Memory[]>([]);
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("general");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConversations();
    loadMemories();
  }, []);

  useEffect(() => {
    if (tab === "conversations") {
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }
  }, [tab, messages]);

  async function loadConversations() {
    setLoadingConvs(true);
    try {
      const data = await getConversations(200);
      setMessages(data.messages || []);
    } catch { /* empty */ }
    setLoadingConvs(false);
  }

  async function loadMemories() {
    try {
      const data = await getMemories();
      setMemories(data.memories || []);
    } catch { /* empty */ }
  }

  async function handleAddMemory() {
    if (!newContent.trim()) return;
    setSaving(true);
    try {
      await createMemory(newContent, newCategory);
      setNewContent("");
      await loadMemories();
    } catch { /* empty */ }
    setSaving(false);
  }

  async function handleDeleteMemory(id: string) {
    try {
      await deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch { /* empty */ }
  }

  // Group messages by date
  function groupByDate(msgs: Message[]) {
    const groups: Record<string, Message[]> = {};
    msgs.forEach((m) => {
      const date = m.created_at
        ? new Date(m.created_at).toLocaleDateString("zh-CN", { month: "long", day: "numeric" })
        : "Unknown";
      if (!groups[date]) groups[date] = [];
      groups[date].push(m);
    });
    return groups;
  }

  const grouped = groupByDate(messages);

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">记忆区</h1>
        <div className="flex rounded-lg border bg-muted/30 p-0.5">
          <button
            onClick={() => setTab("conversations")}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
              tab === "conversations"
                ? "bg-background shadow-sm text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            对话记录
          </button>
          <button
            onClick={() => setTab("memories")}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
              tab === "memories"
                ? "bg-background shadow-sm text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Pixel 的记忆
            {memories.length > 0 && (
              <span className="ml-1.5 rounded-full bg-primary/15 px-1.5 py-0.5 text-xs text-primary">
                {memories.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Conversations Tab */}
      {tab === "conversations" && (
        <div className="flex-1 overflow-y-auto rounded-xl border bg-muted/10 p-4">
          {loadingConvs ? (
            <p className="py-8 text-center text-sm text-muted-foreground animate-pulse">加载中...</p>
          ) : messages.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              还没有对话记录。对着 Pixel 说话后会自动出现在这里。
            </p>
          ) : (
            <div className="space-y-6">
              {Object.entries(grouped).map(([date, msgs]) => (
                <div key={date}>
                  <div className="mb-3 flex items-center gap-3">
                    <div className="h-px flex-1 bg-border" />
                    <span className="text-xs text-muted-foreground">{date}</span>
                    <div className="h-px flex-1 bg-border" />
                  </div>
                  <div className="space-y-2">
                    {msgs.map((m, i) => (
                      <div key={i} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
                        <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                          m.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-card border shadow-sm"
                        }`}>
                          {m.role === "pixel" && <span className="mr-1.5">🪄</span>}
                          {m.content}
                        </div>
                        {m.created_at && (
                          <span className="mt-0.5 text-[10px] text-muted-foreground">
                            {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
      )}

      {/* Memories Tab */}
      {tab === "memories" && (
        <div className="flex flex-1 flex-col overflow-hidden">
          <p className="mb-4 text-sm text-muted-foreground">
            Pixel 在对话中自动积累的记忆。越用越了解你。
          </p>

          {/* Add manual memory */}
          <div className="mb-4 flex gap-2">
            <Input
              placeholder='手动添加，例如："我不喝咖啡"'
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleAddMemory(); }}
              className="flex-1"
            />
            <select
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              className="rounded-lg border bg-background px-3 text-sm"
            >
              {Object.entries(CATEGORY_LABELS).map(([val, label]) => (
                <option key={val} value={val}>{label}</option>
              ))}
            </select>
            <Button onClick={handleAddMemory} disabled={saving || !newContent.trim()}>
              {saving ? "..." : "添加"}
            </Button>
          </div>

          {/* Memory list */}
          <div className="flex-1 overflow-y-auto space-y-2">
            {memories.length === 0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                还没有记忆。和 Pixel 多聊聊，它会慢慢记住你。
              </p>
            ) : (
              memories.map((m) => (
                <div key={m.id} className="flex items-center justify-between rounded-lg border bg-card px-4 py-3">
                  <div className="flex-1">
                    <p className="text-sm">{m.content}</p>
                    <div className="mt-1 flex gap-2">
                      <span className="rounded bg-primary/10 px-2 py-0.5 text-xs text-primary">
                        {CATEGORY_LABELS[m.category] || m.category}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(m.created_at).toLocaleDateString("zh-CN")}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteMemory(m.id)}
                    className="ml-4 text-xs text-muted-foreground hover:text-red-500"
                  >
                    删除
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
