"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStoredUser, logout, getSoul, updateSoul } from "@/lib/api";
import { getLang, setLang, translations, type Lang } from "@/lib/i18n";

type Section = "pixel" | "account";

export default function SettingsPage() {
  const router = useRouter();
  const user = getStoredUser();
  const [section, setSection] = useState<Section>("pixel");
  const [lang, setLangState] = useState<Lang>("zh");

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
    setLangState(getLang());
    const handler = () => setLangState(getLang());
    window.addEventListener("pixel_lang_change", handler);
    return () => window.removeEventListener("pixel_lang_change", handler);
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const data = await getSoul();
        setSoul((prev) => ({ ...prev, ...data }));
        // Sync UI language from saved soul language
        if (data.language && data.language !== "auto") {
          const map: Record<string, Lang> = { zh: "zh", en: "en", no: "no" };
          if (map[data.language]) {
            setLang(map[data.language]);
            setLangState(map[data.language]);
          }
        }
      } catch { /* use defaults */ }
    }
    load();
  }, []);

  function handleLangChange(val: string) {
    setSoul({ ...soul, language: val });
    // Also switch UI language
    const map: Record<string, Lang> = { zh: "zh", en: "en", no: "no" };
    if (map[val]) {
      setLang(map[val]);
      setLangState(map[val]);
    } else {
      // auto — keep current UI lang
    }
  }

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

  const tr = translations[lang];

  const PERSONALITIES = [
    { value: "friendly", label: tr.friendly, desc: tr.friendlyDesc },
    { value: "calm", label: tr.calm, desc: tr.calmDesc },
    { value: "playful", label: tr.playful, desc: tr.playfulDesc },
    { value: "professional", label: tr.professional, desc: tr.professionalDesc },
  ];

  const LANGUAGES = [
    { value: "auto", label: tr.autoDetect },
    { value: "zh", label: "中文" },
    { value: "en", label: "English" },
    { value: "no", label: "Norsk" },
  ];

  const VOICE_STYLES = [
    { value: "warm", label: tr.warm },
    { value: "calm", label: tr.calmVoice },
    { value: "energetic", label: tr.energetic },
    { value: "serious", label: tr.serious },
  ];

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold">{tr.settingsTitle}</h1>

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
          🪄 {tr.pixelPersonality}
        </button>
        <button
          onClick={() => setSection("account")}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
            section === "account"
              ? "bg-background shadow-sm text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {tr.account}
        </button>
      </div>

      {/* Pixel 个性 */}
      {section === "pixel" && (
        <div className="mt-6 space-y-6">
          <p className="text-sm text-muted-foreground">{tr.personalityNote}</p>

          <div>
            <label className="text-sm font-medium">{tr.pixelName}</label>
            <Input
              className="mt-1"
              value={soul.pixel_name}
              onChange={(e) => setSoul({ ...soul, pixel_name: e.target.value })}
              placeholder="Pixel"
            />
          </div>

          <div>
            <label className="text-sm font-medium">{tr.speakingStyle}</label>
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

          <div>
            <label className="text-sm font-medium">{tr.commonLanguage}</label>
            <div className="mt-2 flex flex-wrap gap-2">
              {LANGUAGES.map((l) => (
                <button
                  key={l.value}
                  onClick={() => handleLangChange(l.value)}
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

          <div>
            <label className="text-sm font-medium">{tr.voiceStyle}</label>
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

          <div>
            <label className="text-sm font-medium">{tr.specialNote}</label>
            <p className="mt-0.5 text-xs text-muted-foreground">{tr.specialNotePlaceholder}</p>
            <textarea
              className="mt-2 w-full rounded-lg border bg-background p-3 text-sm"
              rows={3}
              placeholder={tr.pixelInstructions}
              value={soul.custom_prompt}
              onChange={(e) => setSoul({ ...soul, custom_prompt: e.target.value })}
            />
          </div>

          <Button onClick={handleSave} disabled={saving} className="w-full">
            {saving ? tr.saving : saved ? tr.saved : tr.save}
          </Button>
        </div>
      )}

      {/* Account */}
      {section === "account" && (
        <div className="mt-6 space-y-4">
          <div className="rounded-xl border bg-card p-5">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">{tr.accountInfo}</h2>
            <div className="mt-3 space-y-2 text-sm">
              <p><span className="text-muted-foreground">{tr.name}：</span>{user?.name}</p>
              <p><span className="text-muted-foreground">{tr.email}：</span>{user?.email}</p>
            </div>
          </div>

          <div className="rounded-xl border bg-card p-5">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">{tr.device}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{tr.deviceNote}</p>
          </div>

          <div className="rounded-xl border border-red-200 bg-card p-5">
            <h2 className="text-sm font-semibold text-red-500">{tr.signOut}</h2>
            <Button
              variant="destructive"
              className="mt-3"
              onClick={() => { logout(); router.push("/"); }}
            >
              {tr.signOutBtn}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
