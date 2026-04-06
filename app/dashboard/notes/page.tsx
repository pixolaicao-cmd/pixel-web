"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getNotes, createNote, deleteNote, transcribeAudio, summarize } from "@/lib/api";

interface Note {
  id: string;
  title: string;
  summary: string;
  key_points?: string[];
  created_at: string;
}

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [formError, setFormError] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function loadNotes() {
    try {
      const data = await getNotes();
      setNotes(data.notes || []);
    } catch { /* empty */ }
  }

  useEffect(() => { loadNotes(); }, []);

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
        setTranscribing(true);
        try {
          const { text } = await transcribeAudio(blob);
          if (text.trim()) {
            setNewContent((prev) => prev ? prev + " " + text : text);
            if (!newTitle) setNewTitle("Recording " + new Date().toLocaleString());
          }
        } catch { /* empty */ }
        setTranscribing(false);
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

  async function handleSummarize() {
    if (!newContent.trim()) return;
    setSaving(true);
    setFormError(false);
    try {
      const { summary, key_points } = await summarize(newContent);
      const title = newTitle || "Note " + new Date().toLocaleString();
      await createNote(title, newContent, summary, key_points);
      setNewTitle("");
      setNewContent("");
      setShowNew(false);
      await loadNotes();
    } catch {
      setFormError(true);
    }
    setSaving(false);
  }

  async function handleCreate() {
    if (!newTitle.trim()) return;
    setSaving(true);
    setFormError(false);
    try {
      await createNote(newTitle, newContent, "", []);
      setNewTitle("");
      setNewContent("");
      setShowNew(false);
      await loadNotes();
    } catch {
      setFormError(true);
    }
    setSaving(false);
  }

  async function handleDelete(id: string) {
    try {
      await deleteNote(id);
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch { /* empty */ }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Notes</h1>
        <Button onClick={() => setShowNew(!showNew)} variant={showNew ? "outline" : "default"}>
          {showNew ? "Cancel" : "New Note"}
        </Button>
      </div>

      {showNew && (
        <div className="mt-4 space-y-3 rounded-xl border bg-card p-4">
          <Input placeholder="Title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
          <div className="relative">
            <textarea
              placeholder="Content / transcript... or use the mic to record"
              className="w-full rounded-lg border bg-background p-3 text-sm"
              rows={4}
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
            />
            {transcribing && (
              <p className="text-xs text-muted-foreground animate-pulse">Transcribing...</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={recording ? "destructive" : "outline"}
              onMouseDown={startRecording}
              onMouseUp={stopRecording}
              onTouchStart={startRecording}
              onTouchEnd={stopRecording}
              disabled={saving || transcribing}
              title="Hold to record"
            >
              {recording ? "🔴 Recording..." : "🎙️ Hold to Record"}
            </Button>
            <Button
              onClick={handleSummarize}
              disabled={saving || !newContent.trim()}
              variant="outline"
            >
              {saving ? "Summarizing..." : "✨ AI Summarize & Save"}
            </Button>
            <Button onClick={handleCreate} disabled={saving || !newTitle.trim()}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
          {formError && (
            <p className="text-xs text-red-500">Something went wrong. Try again.</p>
          )}
        </div>
      )}

      <div className="mt-6 space-y-3">
        {notes.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No notes yet. Create one or record with your Pixel device.
          </p>
        )}
        {notes.map((n) => (
          <div key={n.id} className="rounded-xl border bg-card p-4">
            <div className="flex items-start justify-between">
              <button className="text-left" onClick={() => setExpanded(expanded === n.id ? null : n.id)}>
                <h3 className="font-semibold">{n.title}</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {new Date(n.created_at).toLocaleDateString()}
                </p>
              </button>
              <button
                onClick={() => handleDelete(n.id)}
                className="text-xs text-muted-foreground hover:text-red-500"
              >
                Delete
              </button>
            </div>
            {expanded === n.id && (
              <div className="mt-3 border-t pt-3">
                {n.summary && <p className="text-sm">{n.summary}</p>}
                {n.key_points && n.key_points.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {n.key_points.map((p, i) => (
                      <li key={i} className="text-sm text-muted-foreground">- {p}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
