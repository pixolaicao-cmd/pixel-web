export type Lang = "zh" | "en" | "no";

export const translations = {
  zh: {
    overview: "概览",
    memory: "记忆区",
    notes: "笔记",
    settings: "设置",
    signOut: "退出登录",
    // Settings
    settingsTitle: "设置",
    pixelPersonality: "Pixel 个性",
    account: "账户",
    personalityNote: "个性越早设置越好——Pixel 会在此基础上慢慢学习你的习惯。",
    pixelName: "Pixel 的名字",
    speakingStyle: "说话风格",
    commonLanguage: "常用语言",
    voiceStyle: "声音风格",
    specialNote: "特别说明（可选）",
    specialNotePlaceholder: "例如：说话不要太长，帮我提醒喝水，用挪威语回答我...",
    pixelInstructions: "给 Pixel 的额外指令...",
    save: "保存设置",
    saving: "保存中...",
    saved: "✅ 已保存",
    autoDetect: "自动识别（推荐）",
    accountInfo: "账户信息",
    name: "名字",
    email: "邮箱",
    device: "设备",
    deviceNote: "暂无设备绑定。硬件出货后可在此绑定 Pixel 实体。",
    signOutBtn: "退出",
    // Personalities
    friendly: "友好温暖",
    friendlyDesc: "像贴心朋友，自然随意",
    calm: "平静舒缓",
    calmDesc: "温和克制，让人放松",
    playful: "活泼幽默",
    playfulDesc: "轻松有趣，偶尔开玩笑",
    professional: "简洁专业",
    professionalDesc: "直接清晰，少废话",
    // Voice
    warm: "温柔",
    calmVoice: "平稳",
    energetic: "活力",
    serious: "沉稳",
  },
  en: {
    overview: "Overview",
    memory: "Memory",
    notes: "Notes",
    settings: "Settings",
    signOut: "Sign out",
    // Settings
    settingsTitle: "Settings",
    pixelPersonality: "Pixel Personality",
    account: "Account",
    personalityNote: "Set your preferences early — Pixel will learn your habits over time.",
    pixelName: "Pixel's Name",
    speakingStyle: "Speaking Style",
    commonLanguage: "Preferred Language",
    voiceStyle: "Voice Style",
    specialNote: "Special Instructions (optional)",
    specialNotePlaceholder: "e.g. Keep answers short, remind me to drink water, always reply in Norwegian...",
    pixelInstructions: "Additional instructions for Pixel...",
    save: "Save Settings",
    saving: "Saving...",
    saved: "✅ Saved",
    autoDetect: "Auto-detect (recommended)",
    accountInfo: "Account Info",
    name: "Name",
    email: "Email",
    device: "Device",
    deviceNote: "No device linked yet. You can bind your Pixel device here when hardware ships.",
    signOutBtn: "Sign Out",
    // Personalities
    friendly: "Friendly & Warm",
    friendlyDesc: "Like a close friend, natural and casual",
    calm: "Calm & Gentle",
    calmDesc: "Soft and soothing, easy to be around",
    playful: "Playful & Fun",
    playfulDesc: "Light-hearted, occasionally witty",
    professional: "Clear & Concise",
    professionalDesc: "Direct and to the point",
    // Voice
    warm: "Warm",
    calmVoice: "Calm",
    energetic: "Energetic",
    serious: "Serious",
  },
  no: {
    overview: "Oversikt",
    memory: "Minne",
    notes: "Notater",
    settings: "Innstillinger",
    signOut: "Logg ut",
    // Settings
    settingsTitle: "Innstillinger",
    pixelPersonality: "Pixel-personlighet",
    account: "Konto",
    personalityNote: "Sett preferansene dine tidlig — Pixel lærer vanene dine over tid.",
    pixelName: "Pixels navn",
    speakingStyle: "Talestil",
    commonLanguage: "Foretrukket språk",
    voiceStyle: "Stemmestil",
    specialNote: "Spesielle instruksjoner (valgfritt)",
    specialNotePlaceholder: "F.eks. Hold svarene korte, påminn meg om å drikke vann...",
    pixelInstructions: "Ekstra instruksjoner til Pixel...",
    save: "Lagre innstillinger",
    saving: "Lagrer...",
    saved: "✅ Lagret",
    autoDetect: "Automatisk (anbefalt)",
    accountInfo: "Kontoinformasjon",
    name: "Navn",
    email: "E-post",
    device: "Enhet",
    deviceNote: "Ingen enhet tilkoblet ennå. Du kan koble til Pixel-enheten din her når maskinvaren er klar.",
    signOutBtn: "Logg ut",
    // Personalities
    friendly: "Vennlig og varm",
    friendlyDesc: "Som en nær venn, naturlig og uformell",
    calm: "Rolig og mild",
    calmDesc: "Myk og beroligende",
    playful: "Leken og morsom",
    playfulDesc: "Lett og underholdende",
    professional: "Klar og konsis",
    professionalDesc: "Direkte og presis",
    // Voice
    warm: "Varm",
    calmVoice: "Rolig",
    energetic: "Energisk",
    serious: "Alvorlig",
  },
};

export function getLang(): Lang {
  if (typeof window === "undefined") return "zh";
  return (localStorage.getItem("pixel_ui_lang") as Lang) || "zh";
}

export function setLang(lang: Lang) {
  localStorage.setItem("pixel_ui_lang", lang);
  window.dispatchEvent(new Event("pixel_lang_change"));
}

export function t(key: keyof typeof translations.zh): string {
  const lang = getLang();
  return translations[lang][key] || translations.zh[key];
}
