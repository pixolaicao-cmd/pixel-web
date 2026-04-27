"use client";

/**
 * Pixel 浏览器模拟器
 * 用浏览器麦克风代替挂件的 PDM mic，后端调用和真挂件完全一致 (/api/voice)。
 *
 * 目的：在硬件到货前，验证核心 AI 体验：
 *   - 端到端延迟（录音结束 → 听到回复）
 *   - STT 准确度（Deepgram）
 *   - AI 回复质量（Gemma 4）
 *   - TTS 自然度（edge-tts）
 *
 * 如果这里感觉不好，挂件只会更差。
 */

import { useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("pixel_token") ?? sessionStorage.getItem("pixel_token");
}

type ServerTiming = {
  setup_ms?: number;
  gemini_ms?: number;
  tts_ms?: number;
  db_ms?: number;
  total_ms?: number;
};

type Exchange = {
  id: number;
  transcript: string;
  reply: string;
  language: string;
  audioUrl?: string;       // 历史记录没有
  // 延迟分段（毫秒），历史记录没有
  recordMs?: number;
  uploadMs?: number;
  ttfbMs?: number;
  totalMs?: number;
  bytes?: number;
  fromHistory?: boolean;   // 标识是从后端拉的历史
  createdAt?: string;
  saved?: boolean;
  historyBytes?: number;
  memoriesBytes?: number;
  memoriesNew?: number;
  soulUsed?: boolean;
  voice?: string;
  serverTiming?: ServerTiming;
};

type MicState = "idle" | "requesting" | "recording" | "processing" | "error";

// VAD（自动停止录音）参数
const VAD_SPEECH_THRESHOLD = 0.08;   // 高于这个 RMS 算"在说话"
const VAD_SILENCE_THRESHOLD = 0.04;  // 低于这个算"静音"
const VAD_SILENCE_MS = 1500;         // 静音持续这么久就自动停（1.5s）
const VAD_MIN_RECORD_MS = 800;       // 录音至少这么久才考虑自动停（防止刚开口就被截）

export default function PixelTestPage() {
  const [micState, setMicState] = useState<MicState>("idle");
  const [error, setError] = useState<string>("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [level, setLevel] = useState(0); // 0-1 录音音量
  const [peakLevel, setPeakLevel] = useState(0); // 本次录音的峰值
  const [liveBytes, setLiveBytes] = useState(0); // 录音中累积字节数
  const [lastRecording, setLastRecording] = useState<{ url: string; bytes: number; ms: number } | null>(null);
  const [vadEnabled, setVadEnabled] = useState(true);
  const [vadStatus, setVadStatus] = useState<string>(""); // 显示 VAD 状态："等你说话…" / "倒计时…"

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recordStartRef = useRef<number>(0);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const exchangeIdRef = useRef(0);
  // VAD refs
  const speechSeenRef = useRef(false);          // 本次录音里是否已经听到过语音
  const lastVoiceAtRef = useRef<number>(0);     // 最后一次"在说话"的时间戳（performance.now()）
  const vadEnabledRef = useRef(true);           // 把 state 同步到 ref，让动画帧循环能拿到最新值
  const autoStoppedRef = useRef(false);         // 防止 VAD 重复触发 stop

  useEffect(() => {
    // 加载历史对话（切页面/刷新都不会丢）
    loadHistory();
    return () => {
      // 卸载清理
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      audioCtxRef.current?.close().catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function clearHistory() {
    if (!confirm("确定清空所有对话记录吗？这会从数据库永久删除。")) return;
    const token = getToken();
    if (!token) return;
    try {
      await fetch(`${API_BASE}/conversations`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      setExchanges([]);
    } catch {
      // ignore
    }
  }

  async function loadHistory() {
    const token = getToken();
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/conversations?limit=50`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data: { messages: Array<{ id: string; role: "user" | "pixel"; content: string; created_at: string }> } = await res.json();
      // 把扁平消息列表配成 (user, pixel) pair → Exchange
      const msgs = data.messages || [];
      const pairs: Exchange[] = [];
      for (let i = 0; i < msgs.length; i++) {
        const m = msgs[i];
        if (m.role === "user") {
          const next = msgs[i + 1];
          if (next && next.role === "pixel") {
            pairs.push({
              id: -(++exchangeIdRef.current), // 历史用负 id 不和实时 exchange 冲突
              transcript: m.content,
              reply: next.content,
              language: "",
              fromHistory: true,
              createdAt: next.created_at,
            });
            i++; // 跳过下一条 pixel
          } else {
            pairs.push({
              id: -(++exchangeIdRef.current),
              transcript: m.content,
              reply: "(无回复)",
              language: "",
              fromHistory: true,
              createdAt: m.created_at,
            });
          }
        } else {
          // 孤立的 pixel 回复
          pairs.push({
            id: -(++exchangeIdRef.current),
            transcript: "",
            reply: m.content,
            language: "",
            fromHistory: true,
            createdAt: m.created_at,
          });
        }
      }
      // 最新的在最上
      setExchanges(pairs.reverse());
    } catch {
      // 静默失败，不影响录音
    }
  }

  // 同步 vadEnabled state → ref（动画帧闭包用 ref 才拿得到最新值）
  useEffect(() => {
    vadEnabledRef.current = vadEnabled;
  }, [vadEnabled]);

  function resetLevel() {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    setLevel(0);
    setVadStatus("");
  }

  function runLevelMeter(analyser: AnalyserNode) {
    const data = new Uint8Array(analyser.fftSize);
    const tick = () => {
      analyser.getByteTimeDomainData(data);
      // RMS 归一化
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / data.length);
      const norm = Math.min(1, rms * 3); // 放大显示
      setLevel(norm);
      setPeakLevel((p) => (norm > p ? norm : p));

      // ── VAD：检测说话 / 静音并自动停止 ─────────────
      if (vadEnabledRef.current && !autoStoppedRef.current) {
        const now = performance.now();
        const elapsedSinceStart = now - recordStartRef.current;

        if (norm > VAD_SPEECH_THRESHOLD) {
          // 在说话：刷新最后语音时间，标记本次确实有人说过话
          speechSeenRef.current = true;
          lastVoiceAtRef.current = now;
          setVadStatus("听到了");
        } else if (norm < VAD_SILENCE_THRESHOLD && speechSeenRef.current) {
          // 静音中：算一下离上次说话过了多久
          const silentFor = now - lastVoiceAtRef.current;
          const remaining = Math.max(0, VAD_SILENCE_MS - silentFor);
          if (elapsedSinceStart >= VAD_MIN_RECORD_MS && silentFor >= VAD_SILENCE_MS) {
            // 触发自动停止
            autoStoppedRef.current = true;
            setVadStatus("自动结束");
            stopRecording();
          } else {
            setVadStatus(`静音 ${(remaining / 1000).toFixed(1)}s…`);
          }
        } else if (!speechSeenRef.current) {
          setVadStatus("等你说话…");
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };
    tick();
  }

  async function startRecording() {
    setError("");
    setMicState("requesting");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        },
      });
      streamRef.current = stream;

      // 音量表
      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      analyserRef.current = analyser;
      runLevelMeter(analyser);

      // 选一个后端接受的 MIME
      const mime = pickSupportedMime();
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      mediaRecorderRef.current = rec;
      chunksRef.current = [];

      rec.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
          setLiveBytes((b) => b + e.data.size);
        }
      };
      rec.onstop = () => {
        const recordMs = performance.now() - recordStartRef.current;
        const mimeType = rec.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: mimeType });
        stopStream();
        resetLevel();
        // 保留本次录音供回放（即使后端报错也能听到自己录到了什么）
        setLastRecording((prev) => {
          if (prev) URL.revokeObjectURL(prev.url);
          return { url: URL.createObjectURL(blob), bytes: blob.size, ms: Math.round(recordMs) };
        });
        sendToPipeline(blob, recordMs, mimeType);
      };

      recordStartRef.current = performance.now();
      setPeakLevel(0);
      setLiveBytes(0);
      // 重置 VAD 状态
      speechSeenRef.current = false;
      lastVoiceAtRef.current = performance.now();
      autoStoppedRef.current = false;
      setVadStatus(vadEnabled ? "等你说话…" : "");
      // timeslice = 500ms：每 500ms 触发一次 ondataavailable，让我们能看到字节数实时增长
      rec.start(500);
      setMicState("recording");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Mic access failed: ${msg}`);
      setMicState("error");
      stopStream();
      resetLevel();
    }
  }

  function stopRecording() {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state !== "inactive") {
      rec.stop();
      setMicState("processing");
    }
  }

  function stopStream() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
  }

  async function sendToPipeline(blob: Blob, recordMs: number, mimeType: string) {
    // 防御：录音过小说明麦克风没真正工作（典型：6 秒只录到 1-2KB）
    // Opus 16kbps 也至少 ~2KB/秒，正常说话应远高于这个
    const minBytesPerSec = 2000;
    if (recordMs > 1500 && blob.size < (recordMs / 1000) * minBytesPerSec) {
      setError(
        `录音几乎没有数据（${(blob.size / 1024).toFixed(1)} KB / ${(recordMs / 1000).toFixed(1)}s）。麦克风没拿到声音。\n` +
        `检查：1) 浏览器地址栏麦克风图标是否被禁；2) macOS 系统设置→声音→输入 选对了设备；3) 别的 app（Zoom/QQ/系统录音）是否占用麦克风；4) 刷新页面重试。`
      );
      setMicState("error");
      return;
    }

    const token = getToken();
    if (!token) {
      setError("Not logged in.");
      setMicState("error");
      return;
    }

    const tStart = performance.now();
    const form = new FormData();
    // 文件名后缀按 MIME 选，后端用 content-type 判断，不看文件名
    const ext = mimeType.includes("webm") ? "webm" :
                mimeType.includes("ogg")  ? "ogg"  :
                mimeType.includes("mp4")  ? "mp4"  : "wav";
    form.append("file", blob, `sim.${ext}`);

    try {
      const res = await fetch(`${API_BASE}/voice`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      const ttfbMs = performance.now() - tStart;

      if (!res.ok) {
        const detail = await safeDetail(res);
        throw new Error(`HTTP ${res.status}: ${detail}`);
      }

      const transcript    = decodeURIComponent(res.headers.get("X-Transcript") ?? "");
      const reply         = decodeURIComponent(res.headers.get("X-Reply") ?? "");
      const language      = res.headers.get("X-Language") ?? "";
      const saved         = res.headers.get("X-Saved") === "1";
      const historyUsed   = parseInt(res.headers.get("X-History-Used") ?? "0", 10);
      const memoriesUsed  = parseInt(res.headers.get("X-Memories-Used") ?? "0", 10);
      const memoriesNew   = parseInt(res.headers.get("X-Memories-New")  ?? "0", 10);
      const soulUsed      = res.headers.get("X-Soul-Used") === "1";
      const voiceUsed     = res.headers.get("X-Voice") ?? "";
      let serverTiming: ServerTiming | undefined;
      try {
        const raw = res.headers.get("X-Timing");
        if (raw) serverTiming = JSON.parse(raw);
      } catch { /* ignore */ }
      console.log(`[voice] saved=${saved} hist=${historyUsed} soul=${soulUsed} voice=${voiceUsed} timing=`, serverTiming);

      const audioBlob = await res.blob();
      const uploadMs  = performance.now() - tStart;
      const audioUrl  = URL.createObjectURL(audioBlob);
      const totalMs   = performance.now() - tStart;

      const exchange: Exchange = {
        id: ++exchangeIdRef.current,
        transcript,
        reply,
        language,
        audioUrl,
        recordMs: Math.round(recordMs),
        uploadMs: Math.round(uploadMs),
        ttfbMs:   Math.round(ttfbMs),
        totalMs:  Math.round(totalMs),
        bytes:    audioBlob.size,
        saved,
        historyBytes: historyUsed,
        memoriesBytes: memoriesUsed,
        memoriesNew,
        soulUsed,
        voice: voiceUsed,
        serverTiming,
      };
      setExchanges((prev) => [exchange, ...prev]);

      // 自动播放
      const audio = new Audio(audioUrl);
      audio.play().catch(() => { /* 浏览器策略：首次需要用户交互，已经有了 */ });

      setMicState("idle");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setMicState("error");
    }
  }

  return (
    <div className="max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Pixel 浏览器模拟器</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          用浏览器麦克风模拟挂件，调用和真机完全一致的 <code className="rounded bg-muted px-1 text-xs">/api/voice</code>。
          验证端到端延迟、STT 准确度、AI 回复质量、TTS 自然度。
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          💡 这里的对话**自动保存到「记忆区 → 对话记录」**（不是 Notater）。
          Notater 是独立的笔记功能，需要去 Notater 页面用录音按钮单独录制。
        </p>
        <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
          ✨ Pixel 会从对话中**自动学习关于你的事实**（喜好/关系/计划等），
          下次它就记得了。卡片上的「✨ 新学到 N 条」就是它刚学到的。
          可在 Minne 页面查看/管理。
        </p>
      </div>

      {/* 录音控件 */}
      <div className="mt-6 rounded-xl border bg-card p-6 shadow-sm">
        <div className="flex items-center gap-6">
          <RecordButton
            state={micState}
            onStart={startRecording}
            onStop={stopRecording}
          />
          <div className="flex-1">
            <div className="flex items-baseline justify-between">
              <StatusLine state={micState} vadStatus={vadStatus} />
              {micState === "recording" && (
                <span className="font-mono text-xs text-muted-foreground">
                  {(liveBytes / 1024).toFixed(1)} KB
                </span>
              )}
            </div>
            <LevelMeter level={level} active={micState === "recording"} />
          </div>
        </div>

        {/* VAD 开关 */}
        <div className="mt-4 flex items-center justify-between rounded-lg bg-muted/30 px-4 py-2 text-xs">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={vadEnabled}
              onChange={(e) => setVadEnabled(e.target.checked)}
              disabled={micState === "recording"}
              className="h-3.5 w-3.5"
            />
            <span>自动停止（静音 {(VAD_SILENCE_MS / 1000).toFixed(1)}s 自动结束 + 上传）</span>
          </label>
          <span className="text-muted-foreground">
            {vadEnabled ? "开" : "关 — 需手动点麦克风结束"}
          </span>
        </div>

        {error && (
          <p className="mt-4 rounded-lg bg-destructive/10 px-4 py-2 text-sm text-destructive">
            {error}
          </p>
        )}

        {lastRecording && (
          <div className="mt-4 rounded-lg border bg-muted/30 px-4 py-3 text-xs">
            <div className="mb-2 flex items-center justify-between text-muted-foreground">
              <span>上次录音回放（用来确认麦克风真的录到声音了）</span>
              <span className="font-mono">
                {(lastRecording.ms / 1000).toFixed(2)}s · {(lastRecording.bytes / 1024).toFixed(1)} KB
                {peakLevel > 0 && <> · 峰值 {Math.round(peakLevel * 100)}%</>}
              </span>
            </div>
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <audio src={lastRecording.url} controls className="h-8 w-full" />
            {peakLevel > 0 && peakLevel < 0.05 && (
              <p className="mt-2 text-destructive">
                ⚠️ 录音音量极低（峰值 &lt; 5%）。检查系统是否选对了麦克风、麦克风是否插紧、是否被静音。
              </p>
            )}
          </div>
        )}

        <p className="mt-4 text-xs text-muted-foreground">
          提示：按住或点击开始录音，再点一次结束。支持中文 / 英文 / 挪威语自动切换。
        </p>
      </div>

      {/* 历史 */}
      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-medium text-muted-foreground">
            对话记录 {exchanges.length > 0 && <span className="font-mono">({exchanges.length})</span>}
          </h2>
          {exchanges.length > 0 && (
            <button
              onClick={clearHistory}
              className="text-xs text-muted-foreground hover:text-destructive"
            >
              清空记录
            </button>
          )}
        </div>
      </div>
      <div className="space-y-4">
        {exchanges.length === 0 ? (
          <div className="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
            还没有对话。点上面的按钮开始。
          </div>
        ) : (
          exchanges.map((ex) => <ExchangeCard key={ex.id} ex={ex} />)
        )}
      </div>
    </div>
  );
}

// ── 子组件 ───────────────────────────────────────────────────

function RecordButton({
  state,
  onStart,
  onStop,
}: {
  state: MicState;
  onStart: () => void;
  onStop: () => void;
}) {
  const recording = state === "recording";
  const busy = state === "requesting" || state === "processing";

  return (
    <button
      onClick={recording ? onStop : onStart}
      disabled={busy}
      aria-label={recording ? "停止录音" : "开始录音"}
      className={`relative flex h-20 w-20 shrink-0 items-center justify-center rounded-full text-3xl shadow-lg transition ${
        recording
          ? "bg-destructive text-destructive-foreground animate-pulse"
          : busy
          ? "bg-muted text-muted-foreground"
          : "bg-primary text-primary-foreground hover:opacity-90"
      } disabled:opacity-60`}
    >
      {recording ? "■" : "🎤"}
    </button>
  );
}

function StatusLine({ state, vadStatus }: { state: MicState; vadStatus?: string }) {
  const map: Record<MicState, string> = {
    idle: "准备就绪 — 点击麦克风开始",
    requesting: "请求麦克风权限…",
    recording: "录音中…",
    processing: "处理中（STT → AI → TTS）…",
    error: "出错了",
  };
  return (
    <p className="text-sm font-medium">
      {map[state]}
      {state === "recording" && vadStatus && (
        <span className="ml-2 text-xs font-normal text-muted-foreground">· {vadStatus}</span>
      )}
    </p>
  );
}

function LevelMeter({ level, active }: { level: number; active: boolean }) {
  const bars = 24;
  return (
    <div className="mt-2 flex h-4 items-end gap-0.5">
      {Array.from({ length: bars }).map((_, i) => {
        const threshold = (i + 1) / bars;
        const on = active && level >= threshold;
        return (
          <div
            key={i}
            className={`w-full rounded-sm transition-all ${
              on
                ? i > bars * 0.75
                  ? "bg-destructive"
                  : i > bars * 0.5
                  ? "bg-yellow-500"
                  : "bg-green-500"
                : "bg-muted"
            }`}
            style={{ height: `${20 + i * 1.5}%` }}
          />
        );
      })}
    </div>
  );
}

function ExchangeCard({ ex }: { ex: Exchange }) {
  const fmt = (ms: number) => (ms / 1000).toFixed(2) + "s";
  const kb = (b: number) => (b / 1024).toFixed(1) + " KB";
  const showStats = !ex.fromHistory && ex.totalMs !== undefined;
  const timeLabel = ex.createdAt
    ? new Date(ex.createdAt).toLocaleString("zh-CN", { hour12: false })
    : null;

  return (
    <div className={`rounded-xl border bg-card p-5 shadow-sm ${ex.fromHistory ? "opacity-90" : ""}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-3">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                你说{ex.language ? `（${ex.language}）` : ""}
              </p>
              {ex.fromHistory && (
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">历史</span>
              )}
              {timeLabel && (
                <span className="text-[10px] text-muted-foreground">{timeLabel}</span>
              )}
            </div>
            <p className="mt-1 text-sm">{ex.transcript || <em className="text-muted-foreground">（空）</em>}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Pixel 回复</p>
            <p className="mt-1 text-sm">{ex.reply || <em className="text-muted-foreground">（空）</em>}</p>
          </div>
        </div>
        {ex.audioUrl && (
          /* eslint-disable-next-line jsx-a11y/media-has-caption */
          <audio src={ex.audioUrl} controls className="h-8 w-48 shrink-0" />
        )}
      </div>

      {showStats && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-muted-foreground sm:grid-cols-4">
            <Stat label="录音" value={fmt(ex.recordMs!)} />
            <Stat label="首字节" value={fmt(ex.ttfbMs!)} />
            <Stat label="总耗时" value={fmt(ex.totalMs!)} emphasize />
            <Stat label="MP3" value={kb(ex.bytes!)} />
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-muted-foreground">
            <span className={ex.saved ? "text-green-600" : "text-destructive"}>
              {ex.saved ? "✓ 已保存到历史" : "✗ 保存失败"}
            </span>
            <span>历史：{ex.historyBytes ?? 0}B</span>
            <span className={(ex.memoriesBytes ?? 0) > 0 ? "text-green-600" : "text-muted-foreground"} title="长期记忆 (Minne) 字节数">
              🧠 记忆：{ex.memoriesBytes ?? 0}B
            </span>
            {(ex.memoriesNew ?? 0) > 0 && (
              <span
                className="rounded-full bg-amber-500/20 px-2 py-0.5 font-medium text-amber-700 dark:text-amber-400"
                title="本次对话 Pixel 自动学到的新事实"
              >
                ✨ 新学到 {ex.memoriesNew} 条
              </span>
            )}
            <span className={ex.soulUsed ? "text-green-600" : ""}>
              {ex.soulUsed ? "✓ Soul 生效" : "Soul 未读到"}
            </span>
            {ex.voice && <span title="实际使用的 TTS 声音">🔊 {ex.voice.split("-").slice(-1)[0].replace("Neural", "")}</span>}
          </div>
          {ex.serverTiming && (
            <div className="mt-2 rounded bg-muted/40 p-2 text-[11px] text-muted-foreground">
              <div className="mb-1 font-medium">后端分段（毫秒）</div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 sm:grid-cols-4">
                <span>setup: <span className="font-mono">{ex.serverTiming.setup_ms ?? "?"}</span></span>
                <span className={(ex.serverTiming.gemini_ms ?? 0) > 3000 ? "text-orange-600" : ""}>
                  gemini: <span className="font-mono">{ex.serverTiming.gemini_ms ?? "?"}</span>
                </span>
                <span className={(ex.serverTiming.tts_ms ?? 0) > 2000 ? "text-orange-600" : ""}>
                  tts: <span className="font-mono">{ex.serverTiming.tts_ms ?? "?"}</span>
                </span>
                <span>db: <span className="font-mono">{ex.serverTiming.db_ms ?? "?"}</span></span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value, emphasize = false }: { label: string; value: string; emphasize?: boolean }) {
  return (
    <div className="flex items-baseline justify-between rounded-md bg-muted/40 px-2 py-1">
      <span>{label}</span>
      <span className={`font-mono ${emphasize ? "font-semibold text-foreground" : ""}`}>{value}</span>
    </div>
  );
}

// ── 工具函数 ─────────────────────────────────────────────────

function pickSupportedMime(): string | null {
  // 优先顺序：后端都接受的格式
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  if (typeof MediaRecorder === "undefined") return null;
  for (const m of candidates) {
    if (MediaRecorder.isTypeSupported(m)) return m;
  }
  return null;
}

async function safeDetail(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return typeof data?.detail === "string" ? data.detail : JSON.stringify(data);
  } catch {
    try {
      return await res.text();
    } catch {
      return res.statusText || "unknown error";
    }
  }
}
