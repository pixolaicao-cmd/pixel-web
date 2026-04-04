"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { chatWithPixel, speakText, transcribeAudio } from "@/lib/api";

interface Message {
  role: "user" | "pixel";
  content: string;
}

function detectLang(text: string): string {
  if (/[\u4e00-\u9fff]/.test(text)) return "zh";
  if (/[\u00C0-\u024F\u00e6\u00f8\u00e5]/i.test(text)) return "no";
  return "en";
}

export default function DemoPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "pixel", content: "Hi! I'm Pixel, your AI companion. Type anything to start chatting!" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [recording, setRecording] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function playAudio(text: string) {
    try {
      setPlaying(true);
      const lang = detectLang(text);
      const blob = await speakText(text, lang);
      const url = URL.createObjectURL(blob);

      if (audioRef.current) {
        audioRef.current.pause();
      }

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        setPlaying(false);
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => setPlaying(false);
      await audio.play();
    } catch {
      setPlaying(false);
    }
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
            setMessages((prev) => [...prev, { role: "user", content: text }]);
            const data = await chatWithPixel(text);
            setMessages((prev) => [...prev, { role: "pixel", content: data.reply }]);
            playAudio(data.reply);
          }
        } catch {
          setMessages((prev) => [...prev, { role: "pixel", content: "Could not transcribe audio. Please try again." }]);
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
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const data = await chatWithPixel(text);
      setMessages((prev) => [...prev, { role: "pixel", content: data.reply }]);
      playAudio(data.reply);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "pixel", content: "Oops, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col px-4 py-8">
      <div className="mb-6 text-center">
        <h1 className="text-3xl font-bold">Try Pixel</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Chat with Pixel right here. It will reply with text and voice.
        </p>
      </div>

      {/* Chat area */}
      <div className="flex-1 space-y-4 overflow-y-auto rounded-xl border bg-muted/20 p-4" style={{ minHeight: "400px", maxHeight: "60vh" }}>
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-card border shadow-sm"
              }`}
            >
              {m.role === "pixel" && (
                <span className="mr-1.5 text-base">&#x1FA84;</span>
              )}
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl border bg-card px-4 py-2.5 text-sm shadow-sm">
              <span className="mr-1.5 text-base">&#x1FA84;</span>
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Say something to Pixel..."
          disabled={loading}
          className="flex-1"
        />
        <Button type="submit" disabled={loading || !input.trim()}>
          Send
        </Button>
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

      {playing && (
        <p className="mt-2 text-center text-xs text-muted-foreground animate-pulse">
          Pixel is speaking...
        </p>
      )}

      <p className="mt-4 text-center text-xs text-muted-foreground">
        Powered by Grok AI + Edge TTS. Try Chinese, Norwegian, or English.
      </p>
    </div>
  );
}
