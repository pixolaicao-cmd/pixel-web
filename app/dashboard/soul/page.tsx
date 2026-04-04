"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getSoul, updateSoul } from "@/lib/api";

export default function SoulPage() {
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
      setTimeout(() => setSaved(false), 2000);
    } catch { /* empty */ }
    setSaving(false);
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold">Pixel Soul</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Customize your Pixel&apos;s personality and behavior.
      </p>

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
