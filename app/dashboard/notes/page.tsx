"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getNotes, createNote, deleteNote, transcribeAudio, summarize, summarizeDocument, exportNoteDocx, exportNoteTxt, exportNotePrint, importFileToMemory } from "@/lib/api";

interface Note {
  id: string;
  title: string;
  summary: string;
  key_points?: string[];
  markdown?: string;
  created_at: string;
}

function downloadMarkdown(content: string, title: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title.replace(/[^a-z0-9\u4e00-\u9fa5]/gi, "_")}.md`;
  a.click();
  URL.revokeObjectURL(url);
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
  const [docMode, setDocMode] = useState(false);
  const [previewMarkdown, setPreviewMarkdown] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
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
    setPreviewMarkdown(null);
    try {
      if (docMode) {
        const { summary, key_points, markdown } = await summarizeDocument(newContent);
        const title = newTitle || "Document " + new Date().toLocaleString();
        await createNote(title, newContent, summary, key_points, markdown);
        setPreviewMarkdown(markdown);
        setNewTitle("");
        setNewContent("");
        setShowNew(false);
        await loadNotes();
      } else {
        const { summary, key_points } = await summarize(newContent);
        const title = newTitle || "Note " + new Date().toLocaleString();
        await createNote(title, newContent, summary, key_points);
        setNewTitle("");
        setNewContent("");
        setShowNew(false);
        await loadNotes();
      }
    } catch {
      setFormError(true);
    }
    setSaving(false);
  }

  async function handleFileImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportResult(null);
    try {
      const res = await importFileToMemory(file);
      setImportResult(`✅ "${res.filename}" imported — ${res.total_chars.toLocaleString()} chars saved to Memory`);
    } catch (err) {
      setImportResult(`❌ ${err instanceof Error ? err.message : "Import failed"}`);
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
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
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            title="Import PDF / Word / PPT / Excel into Memory"
          >
            {importing ? "Importing…" : "📎 Import to Memory"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.pptx,.xlsx,.txt,.html,.md"
            className="hidden"
            onChange={handleFileImport}
          />
          <Button onClick={() => setShowNew(!showNew)} variant={showNew ? "outline" : "default"}>
            {showNew ? "Cancel" : "New Note"}
          </Button>
        </div>
      </div>

      {importResult && (
        <p className={`mt-3 rounded-lg px-4 py-2 text-sm ${importResult.startsWith("✅") ? "bg-green-500/10 text-green-700 dark:text-green-400" : "bg-red-500/10 text-red-600"}`}>
          {importResult}
        </p>
      )}

      {/* 上次生成的文档快速下载 */}
      {previewMarkdown && (
        <div className="mt-4 rounded-xl border border-green-500/30 bg-green-500/10 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-green-700 dark:text-green-400">Document created!</p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => downloadMarkdown(previewMarkdown, "document")}
            >
              ⬇ Download .md
            </Button>
          </div>
        </div>
      )}

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

          {/* 文档模式切换 */}
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <div
              className={`relative h-5 w-9 rounded-full transition-colors ${docMode ? "bg-primary" : "bg-muted"}`}
              onClick={() => setDocMode(!docMode)}
            >
              <div className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${docMode ? "translate-x-4" : "translate-x-0.5"}`} />
            </div>
            <span className={docMode ? "font-medium" : "text-muted-foreground"}>Document Mode</span>
            {docMode && <span className="text-xs text-muted-foreground">— generates structured Markdown with title, summary, action items</span>}
          </label>

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
              {saving
                ? (docMode ? "Generating..." : "Summarizing...")
                : (docMode ? "📄 Create Document" : "✨ AI Summarize & Save")}
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
                  {n.markdown && <span className="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">Document</span>}
                </p>
              </button>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => exportNotePrint(n.id)}
                  className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  title="Print / Save as PDF"
                >PDF</button>
                <button
                  onClick={() => exportNoteDocx(n.id)}
                  className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  title="Download Word (.docx)"
                >DOCX</button>
                <button
                  onClick={() => exportNoteTxt(n.id)}
                  className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  title="Download plain text"
                >TXT</button>
                {n.markdown && (
                  <button
                    onClick={() => downloadMarkdown(n.markdown!, n.title)}
                    className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                    title="Download Markdown"
                  >.md</button>
                )}
                <span className="mx-1 text-muted-foreground/30">|</span>
                <button
                  onClick={() => handleDelete(n.id)}
                  className="text-xs text-muted-foreground hover:text-red-500"
                >Delete</button>
              </div>
            </div>
            {expanded === n.id && (
              <div className="mt-3 border-t pt-3">
                {n.markdown ? (
                  <pre className="whitespace-pre-wrap rounded-lg bg-muted p-3 text-sm font-mono leading-relaxed">
                    {n.markdown}
                  </pre>
                ) : (
                  <>
                    {n.summary && <p className="text-sm">{n.summary}</p>}
                    {n.key_points && n.key_points.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {n.key_points.map((p, i) => (
                          <li key={i} className="text-sm text-muted-foreground">- {p}</li>
                        ))}
                      </ul>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
