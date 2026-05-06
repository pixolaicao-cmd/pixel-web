"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getSoul, updateSoul } from "@/lib/api";

type SoulState = {
  pixel_name: string;
  personality: string;
  language: string;
  voice_style: string;
  custom_prompt: string;
  recording_mode: boolean;
  translation_mode: boolean;
  translation_lang_a: string | null;
  translation_lang_b: string | null;
};

export default function SoulPage() {
  const [soul, setSoul] = useState<SoulState>({
    pixel_name: "Pixel",
    personality: "friendly",
    language: "auto",
    voice_style: "warm",
    custom_prompt: "",
    recording_mode: false,
    translation_mode: false,
    translation_lang_a: null,
    translation_lang_b: null,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getSoul();
        setSoul((prev) => ({ ...prev, ...data }));
      } catch { /* use defaults */ }
    }
    load();
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await updateSoul(soul);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { /* empty */ }
    setSaving(false);
  }

  // 即时切换：开关类设置不走"修改后点保存"，避免用户忘记保存导致状态不一致
  async function toggleField(
    key: "recording_mode" | "translation_mode",
    next: boolean,
    extras: Partial<SoulState> = {},
  ) {
    setToggling(key);
    const optimistic = { ...soul, [key]: next, ...extras };
    setSoul(optimistic);
    try {
      await updateSoul({ [key]: next, ...extras });
    } catch {
      // 回滚
      setSoul(soul);
    }
    setToggling(null);
  }

  async function setTranslationPair(a: string, b: string) {
    setToggling("translation_pair");
    const optimistic = {
      ...soul,
      translation_mode: true,
      translation_lang_a: a,
      translation_lang_b: b,
    };
    setSoul(optimistic);
    try {
      await updateSoul({
        translation_mode: true,
        translation_lang_a: a,
        translation_lang_b: b,
      });
    } catch {
      setSoul(soul);
    }
    setToggling(null);
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold">Pixel Soul</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Customize your Pixel&apos;s personality and behavior.
      </p>

      {/* 模式开关 — 比语音触发更稳定的主路径 */}
      <div className="mt-6 rounded-xl border bg-card p-4 space-y-4">
        <div>
          <h2 className="text-sm font-semibold">模式开关 / Mode Switches</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            语音触发偶尔不灵（识别错、口音、噪音），用这里点一下最稳。
          </p>
        </div>

        {/* Recording mode */}
        <div className="flex items-start justify-between gap-4 rounded-lg border bg-background p-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">记录模式 / Recording</span>
              {soul.recording_mode ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-700 dark:bg-red-950 dark:text-red-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
                  REC
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {soul.recording_mode
                ? "对话永久存档，可以在 Conversations 里翻看。"
                : "默认 24 小时临时上下文，到期自动清空。"}
            </p>
          </div>
          <button
            type="button"
            disabled={toggling === "recording_mode"}
            onClick={() => toggleField("recording_mode", !soul.recording_mode)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors ${
              soul.recording_mode ? "bg-red-500" : "bg-muted"
            } disabled:opacity-50`}
            aria-pressed={soul.recording_mode}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                soul.recording_mode ? "translate-x-5" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>

        {/* Translation mode */}
        <div className="rounded-lg border bg-background p-3">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">翻译模式 / Translation</span>
                {soul.translation_mode &&
                soul.translation_lang_a &&
                soul.translation_lang_b ? (
                  <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                    {soul.translation_lang_a.toUpperCase()} ⇄{" "}
                    {soul.translation_lang_b.toUpperCase()}
                  </span>
                ) : null}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Pixel 只做翻译，不闲聊。讲一种语言 → 回另一种。
              </p>
            </div>
            <button
              type="button"
              disabled={toggling === "translation_mode"}
              onClick={() =>
                toggleField(
                  "translation_mode",
                  !soul.translation_mode,
                  soul.translation_mode
                    ? { translation_lang_a: null, translation_lang_b: null }
                    : !soul.translation_lang_a || !soul.translation_lang_b
                    ? { translation_lang_a: "zh", translation_lang_b: "no" }
                    : {},
                )
              }
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors ${
                soul.translation_mode ? "bg-blue-500" : "bg-muted"
              } disabled:opacity-50`}
              aria-pressed={soul.translation_mode}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                  soul.translation_mode ? "translate-x-5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>

          {soul.translation_mode ? (
            <div className="mt-3 grid grid-cols-3 gap-2">
              {[
                { a: "zh", b: "no", label: "中 ⇄ 挪" },
                { a: "zh", b: "en", label: "中 ⇄ 英" },
                { a: "en", b: "no", label: "EN ⇄ NO" },
              ].map((p) => {
                const active =
                  soul.translation_lang_a === p.a &&
                  soul.translation_lang_b === p.b;
                return (
                  <button
                    key={`${p.a}-${p.b}`}
                    type="button"
                    disabled={toggling !== null}
                    onClick={() => setTranslationPair(p.a, p.b)}
                    className={`rounded-lg border px-2 py-1.5 text-xs font-medium transition-colors ${
                      active
                        ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                        : "hover:bg-muted"
                    } disabled:opacity-50`}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-8 space-y-6">
        <div>
          <label className="text-sm font-medium">Pixel&apos;s Name</label>
          <Input
            className="mt-1"
            value={soul.pixel_name}
            onChange={(e) => setSoul({ ...soul, pixel_name: e.target.value })}
            placeholder="Pixel"
          />
        </div>

        <div>
          <label className="text-sm font-medium">Personality</label>
          <select
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2 text-sm"
            value={soul.personality}
            onChange={(e) => setSoul({ ...soul, personality: e.target.value })}
          >
            <option value="friendly">Friendly — warm and casual</option>
            <option value="professional">Professional — clear and concise</option>
            <option value="playful">Playful — fun and energetic</option>
            <option value="calm">Calm — gentle and soothing</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-medium">Language</label>
          <select
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2 text-sm"
            value={soul.language}
            onChange={(e) => setSoul({ ...soul, language: e.target.value })}
          >
            <option value="auto">Auto-detect</option>
            <option value="zh">Chinese</option>
            <option value="en">English</option>
            <option value="no">Norwegian</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-medium">Voice Style</label>
          <select
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2 text-sm"
            value={soul.voice_style}
            onChange={(e) => setSoul({ ...soul, voice_style: e.target.value })}
          >
            <option value="warm">Warm</option>
            <option value="energetic">Energetic</option>
            <option value="calm">Calm</option>
            <option value="serious">Serious</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-medium">Custom Instructions</label>
          <textarea
            className="mt-1 w-full rounded-lg border bg-background p-3 text-sm"
            rows={3}
            placeholder="Optional: add special instructions for your Pixel..."
            value={soul.custom_prompt}
            onChange={(e) => setSoul({ ...soul, custom_prompt: e.target.value })}
          />
        </div>

        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : saved ? "Saved!" : "Save Settings"}
        </Button>
      </div>
    </div>
  );
}
