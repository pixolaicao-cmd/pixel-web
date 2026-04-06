"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getConversations, saveMessage, chatWithPixel, speakText, transcribeAudio, createNote, summarize } from "@/lib/api";

interface Message {
  id?: string;
  role: "user" | "pixel";
  content: string;
  created_at?: string;
}

function detectLang(text: string): string {
  if (/[\u4e00-\u9fff]/.test(text)) return "zh";
  if (/[\u00C0-\u024F\u00e6\u00f8\u00e5]/i.test(text)) return "no";
  return "en";
}

export default function ConversationsPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedNote, setSavedNote] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const data = await getConversations(100);
        setMessages(data.messages || []);
      } catch { /* empty */ }
    }
    load();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function saveAsNote() {
    if (messages.length === 0) return;
    setSaving(true);
    setSavedNote(false);
    try {
      const transcript = messages.map(m => `${m.role === "user" ? "我" : "Pixel"}: ${m.content}`).join("\n");
      const { summary, key_points } = await summarize(transcript);
      const title = "对话记录 " + new Date().toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
      await createNote(title, transcript, summary, key_points);
      setSavedNote(true);
      setTimeout(() => setSavedNote(false), 3000);
    } catch { /* empty */ }
    setSaving(false);
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setLoading(true);
        try {
          const { text } = await transcribeAudio(blob);
          if (text.trim()) {
            const userMsg: Message = { role: "user", content: text };
            setMessages((prev) => [...prev, userMsg]);
            await saveMessage("user", text);
            const data = await chatWithPixel(text);
            const pixelMsg: Message = { role: "pixel", content: data.reply };
            setMessages((prev) => [...prev, pixelMsg]);
            await saveMessage("pixel", data.reply);
            try {
              const audioBlob = await speakText(data.reply, detectLang(data.reply));
              const url = URL.createObjectURL(audioBlob);
              const audio = new Audio(url);
              audio.onended = () => URL.revokeObjectURL(url);
              await audio.play();
            } catch { /* audio optional */ }
          }
        } catch {
          setMessages((prev) => [...prev, { role: "pixel", content: "Could not transcribe audio." }]);
        } finally {
          setLoading(false);
        }
      };
      mr.start();
      setRecording(true);
    } catch {
      alert("Microphone access denied.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      await saveMessage("user", text);
      const data = await chatWithPixel(text);
      const pixelMsg: Message = { role: "pixel", content: data.reply };
      setMessages((prev) => [...prev, pixelMsg]);
      await saveMessage("pixel", data.reply);

      // Play audio
      try {
        const blob = await speakText(data.reply, detectLang(data.reply));
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => URL.revokeObjectURL(url);
        await audio.play();
      } catch { /* audio optional */ }
    } catch {
      setMessages((prev) => [...prev, { role: "pixel", content: "Something went wrong. Try again." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Conversations</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={saveAsNote}
          disabled={saving || messages.length === 0}
        >
          {saving ? "Saving..." : savedNote ? "✅ Saved!" : "✨ Save as Note"}
        </Button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border bg-muted/20 p-4">
        {messages.length === 0 && (
          <p className="text-center text-sm text-muted-foreground py-8">
            No conversations yet. Say something to Pixel!
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
              m.role === "user" ? "bg-primary text-primary-foreground" : "bg-card border shadow-sm"
            }`}>
              {m.role === "pixel" && <span className="mr-1.5">&#x1FA84;</span>}
              {m.content}
            </div>
            {m.created_at && (
              <span className="mt-0.5 text-[10px] text-muted-foreground">
                {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl border bg-card px-4 py-2.5 text-sm shadow-sm">
              <span className="mr-1.5">&#x1FA84;</span>
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Talk to Pixel..."
          disabled={loading}
          className="flex-1"
        />
        <Button type="submit" disabled={loading || !input.trim()}>Send</Button>
        <Button
          type="button"
          variant={recording ? "destructive" : "outline"}
          disabled={loading}
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
          title="Hold to speak"
        >
          {recording ? "🔴" : "🎙️"}
        </Button>
      </form>
    </div>
  );
}
