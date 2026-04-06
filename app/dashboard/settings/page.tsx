"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStoredUser, logout, getSoul, updateSoul } from "@/lib/api";

type Section = "pixel" | "account";

const PERSONALITIES = [
  { value: "friendly", label: "友好温暖", desc: "像贴心朋友，自然随意" },
  { value: "calm", label: "平静舒缓", desc: "温和克制，让人放松" },
  { value: "playful", label: "活泼幽默", desc: "轻松有趣，偶尔开玩笑" },
  { value: "professional", label: "简洁专业", desc: "直接清晰，少废话" },
];

const LANGUAGES = [
  { value: "auto", label: "自动识别（推荐）" },
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
  { value: "no", label: "Norsk" },
];

const VOICE_STYLES = [
  { value: "warm", label: "温柔" },
  { value: "calm", label: "平稳" },
  { value: "energetic", label: "活力" },
  { value: "serious", label: "沉稳" },
];

export default function SettingsPage() {
  const router = useRouter();
  const user = getStoredUser();
  const [section, setSection] = useState<Section>("pixel");

  const [soul, setSoul] = useState({
    pixel_name: "Pixel",
    personality: "friendly",
    language: "auto",
    voice_style: "warm",
    custom_prompt: "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

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
      setTimeout(() => setSaved(false), 2500);
    } catch { /* empty */ }
    setSaving(false);
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold">设置</h1>

      {/* Tab switcher */}
      <div className="mt-4 flex gap-1 rounded-lg border bg-muted/30 p-0.5 w-fit">
        <button
          onClick={() => setSection("pixel")}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
            section === "pixel"
              ? "bg-background shadow-sm text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          🪄 Pixel 个性
        </button>
        <button
          onClick={() => setSection("account")}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
            section === "account"
              ? "bg-background shadow-sm text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          账户
        </button>
      </div>

      {/* Pixel 个性 */}
      {section === "pixel" && (
        <div className="mt-6 space-y-6">
          <p className="text-sm text-muted-foreground">
            个性越早设置越好——Pixel 会在此基础上慢慢学习你的习惯。
          </p>

          {/* Name */}
          <div>
            <label className="text-sm font-medium">Pixel 的名字</label>
            <Input
              className="mt-1"
              value={soul.pixel_name}
              onChange={(e) => setSoul({ ...soul, pixel_name: e.target.value })}
              placeholder="Pixel"
            />
          </div>

          {/* Personality */}
          <div>
            <label className="text-sm font-medium">说话风格</label>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {PERSONALITIES.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setSoul({ ...soul, personality: p.value })}
                  className={`rounded-xl border p-3 text-left transition ${
                    soul.personality === p.value
                      ? "border-primary bg-primary/5"
                      : "bg-card hover:border-primary/40"
                  }`}
                >
                  <p className="text-sm font-medium">{p.label}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{p.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Language */}
          <div>
            <label className="text-sm font-medium">常用语言</label>
            <div className="mt-2 flex flex-wrap gap-2">
              {LANGUAGES.map((l) => (
                <button
                  key={l.value}
                  onClick={() => setSoul({ ...soul, language: l.value })}
                  className={`rounded-full border px-4 py-1.5 text-sm transition ${
                    soul.language === l.value
                      ? "border-primary bg-primary/5 font-medium text-foreground"
                      : "text-muted-foreground hover:border-primary/40"
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          {/* Voice */}
          <div>
            <label className="text-sm font-medium">声音风格</label>
            <div className="mt-2 flex flex-wrap gap-2">
              {VOICE_STYLES.map((v) => (
                <button
                  key={v.value}
                  onClick={() => setSoul({ ...soul, voice_style: v.value })}
                  className={`rounded-full border px-4 py-1.5 text-sm transition ${
                    soul.voice_style === v.value
                      ? "border-primary bg-primary/5 font-medium text-foreground"
                      : "text-muted-foreground hover:border-primary/40"
                  }`}
                >
                  {v.label}
                </button>
              ))}
            </div>
          </div>

          {/* Custom instructions */}
          <div>
            <label className="text-sm font-medium">特别说明（可选）</label>
            <p className="mt-0.5 text-xs text-muted-foreground">
              例如：说话不要太长，帮我提醒喝水，用挪威语回答我...
            </p>
            <textarea
              className="mt-2 w-full rounded-lg border bg-background p-3 text-sm"
              rows={3}
              placeholder="给 Pixel 的额外指令..."
              value={soul.custom_prompt}
              onChange={(e) => setSoul({ ...soul, custom_prompt: e.target.value })}
            />
          </div>

          <Button onClick={handleSave} disabled={saving} className="w-full">
            {saving ? "保存中..." : saved ? "✅ 已保存" : "保存设置"}
          </Button>
        </div>
      )}

      {/* Account */}
      {section === "account" && (
        <div className="mt-6 space-y-4">
          <div className="rounded-xl border bg-card p-5">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">账户信息</h2>
            <div className="mt-3 space-y-2 text-sm">
              <p><span className="text-muted-foreground">名字：</span>{user?.name}</p>
              <p><span className="text-muted-foreground">邮箱：</span>{user?.email}</p>
            </div>
          </div>

          <div className="rounded-xl border bg-card p-5">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">设备</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              暂无设备绑定。硬件出货后可在此绑定 Pixel 实体。
            </p>
          </div>

          <div className="rounded-xl border border-red-200 bg-card p-5">
            <h2 className="text-sm font-semibold text-red-500">退出登录</h2>
            <Button
              variant="destructive"
              className="mt-3"
              onClick={() => { logout(); router.push("/"); }}
            >
              退出
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
