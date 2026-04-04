import { Badge } from "@/components/ui/badge";

const FEATURES = [
  {
    icon: "\uD83C\uDFA4",
    badge: "Core",
    title: "Voice Conversations",
    desc: "Just speak naturally — Pixel listens, understands, and responds with a warm, friendly voice. No buttons, no screens, no distractions.",
    details: [
      "Supports Chinese, Norwegian, and English",
      "Automatic language detection and switching",
      "Natural voice responses via Edge TTS",
      "Wake word activation: just say \"Pixel\"",
    ],
  },
  {
    icon: "\uD83D\uDCDD",
    badge: "Core",
    title: "Smart Note-Taking",
    desc: "Say \"start recording\" during a meeting, lecture, or brainstorm. Pixel records everything and generates structured summaries.",
    details: [
      "Real-time audio recording and transcription",
      "AI-powered summary with key points extracted",
      "Download notes as PDF or Markdown",
      "Action items automatically highlighted",
    ],
  },
  {
    icon: "\uD83E\uDDE0",
    badge: "Core",
    title: "Active Memory",
    desc: "Tell Pixel \"remember that I like oat milk\" and it never forgets. Your preferences, schedules, and important details — always remembered.",
    details: [
      "Natural language memory storage",
      "Contextual recall during conversations",
      "Memory management via companion app",
      "Privacy-first: your data, your control",
    ],
  },
  {
    icon: "\uD83C\uDF0D",
    badge: "Core",
    title: "Real-time Translation",
    desc: "Perfect for multilingual environments. Pixel translates between Chinese, Norwegian, and English in real time.",
    details: [
      "Sentence-level live translation",
      "Optimized for Chinese-Norwegian pairs",
      "Simple phrases processed locally for speed",
      "Complex sentences handled via cloud AI",
    ],
  },
];

export default function FeaturesPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      <h1 className="text-center text-4xl font-bold">What Pixel Can Do</h1>
      <p className="mt-4 text-center text-muted-foreground">
        Four core capabilities designed for hands-free living.
      </p>

      <div className="mt-16 space-y-16">
        {FEATURES.map((f) => (
          <section key={f.title} className="rounded-xl border bg-card p-8">
            <div className="flex items-start gap-4">
              <span className="text-4xl">{f.icon}</span>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-2xl font-bold">{f.title}</h2>
                  <Badge variant="secondary">{f.badge}</Badge>
                </div>
                <p className="mt-2 text-muted-foreground">{f.desc}</p>
                <ul className="mt-4 space-y-2">
                  {f.details.map((d) => (
                    <li key={d} className="flex items-start gap-2 text-sm">
                      <span className="mt-0.5 text-green-500">&#10003;</span>
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
