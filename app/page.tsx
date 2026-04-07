import Link from "next/link";
import { buttonVariants } from "@/lib/button-variants";

const FEATURES = [
  {
    icon: "🎙️",
    title: "Voice Conversations",
    desc: "Talk to Pixel naturally. It understands Chinese, Norwegian, and English — and switches automatically.",
  },
  {
    icon: "📄",
    title: "Document Mode",
    desc: "Record a meeting or lecture. Pixel turns it into a structured document with summaries, key points, and action items.",
  },
  {
    icon: "🧠",
    title: "Active Memory",
    desc: "Pixel remembers what matters. The more you use it, the better it knows you.",
  },
  {
    icon: "📷",
    title: "See the World",
    desc: "Point at anything. Pixel reads menus, identifies objects, and describes what it sees — powered by Gemma 4 vision.",
  },
  {
    icon: "🌍",
    title: "Real-time Translation",
    desc: "Chinese, Norwegian, English. Instant. No app switching, no typing.",
  },
  {
    icon: "☁️",
    title: "Your Personal Cloud",
    desc: "All your conversations, notes, and memories — organized and accessible from any device.",
  },
];

const SPECS = [
  { label: "AI Model", value: "Gemma 4 (Google)" },
  { label: "Languages", value: "Chinese · Norwegian · English" },
  { label: "Connectivity", value: "WiFi + 4G/5G" },
  { label: "Display", value: "OLED — animated expressions" },
  { label: "Camera", value: "Multimodal vision" },
  { label: "Water resistance", value: "IP55" },
];

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden px-4 py-28 text-center md:py-40">
        {/* Background glow */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-[500px] w-[500px] rounded-full bg-primary/10 blur-[120px]" />
        </div>

        <div className="relative">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10 text-5xl shadow-inner">
            🪄
          </div>
          <div className="mx-auto mb-4 w-fit rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-medium text-primary">
            Hardware shipping Q3 2026
          </div>
          <h1 className="mx-auto max-w-3xl text-5xl font-bold leading-tight tracking-tight md:text-7xl">
            Your AI friend,{" "}
            <span className="bg-gradient-to-r from-primary to-primary/50 bg-clip-text text-transparent">
              around your neck.
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg text-muted-foreground">
            Pixel is a tiny wearable AI pendant. Conversations, notes, translation, memory — completely hands-free, always with you.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link href="/register" className={buttonVariants({ size: "lg" })}>
              Create Account
            </Link>
            <Link href="/pricing" className={buttonVariants({ variant: "outline", size: "lg" })}>
              See Pricing
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t px-4 py-24">
        <div className="mx-auto max-w-5xl">
          <p className="mb-3 text-center text-sm font-medium text-primary">What Pixel does</p>
          <h2 className="mb-4 text-center text-3xl font-bold md:text-4xl">
            Built for real life
          </h2>
          <p className="mx-auto mb-16 max-w-lg text-center text-muted-foreground">
            Not a gadget. A companion that learns, remembers, and helps — quietly hanging around your neck.
          </p>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="group rounded-2xl border bg-card p-6 shadow-sm transition hover:border-primary/30 hover:shadow-md"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/8 text-2xl">
                  {f.icon}
                </div>
                <h3 className="text-base font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t bg-muted/20 px-4 py-24">
        <div className="mx-auto max-w-4xl">
          <p className="mb-3 text-center text-sm font-medium text-primary">How it works</p>
          <h2 className="mb-16 text-center text-3xl font-bold md:text-4xl">Simple as 1-2-3</h2>
          <div className="grid gap-8 md:grid-cols-3">
            {[
              { step: "01", title: "Wear it", desc: "Hang Pixel around your neck. Press the button to wake it up." },
              { step: "02", title: "Talk to it", desc: "Speak naturally. Record meetings, ask questions, request translations." },
              { step: "03", title: "Review anytime", desc: "Open the web app to see your notes, memories, and conversation history." },
            ].map((s) => (
              <div key={s.step} className="text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-lg font-bold text-primary">
                  {s.step}
                </div>
                <h3 className="text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Specs */}
      <section className="border-t px-4 py-24">
        <div className="mx-auto max-w-3xl">
          <p className="mb-3 text-center text-sm font-medium text-primary">Under the hood</p>
          <h2 className="mb-12 text-center text-3xl font-bold md:text-4xl">Built to last</h2>
          <div className="grid divide-y rounded-2xl border bg-card shadow-sm sm:grid-cols-2 sm:divide-x sm:divide-y-0">
            {SPECS.map((s, i) => (
              <div
                key={s.label}
                className={`px-6 py-5 ${i >= 2 ? "border-t" : ""}`}
              >
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">{s.label}</p>
                <p className="mt-1 font-semibold">{s.value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t bg-muted/20 px-4 py-24 text-center">
        <div className="mx-auto max-w-2xl">
          <span className="text-5xl">🪄</span>
          <h2 className="mt-6 text-3xl font-bold md:text-4xl">Ready to meet Pixel?</h2>
          <p className="mt-4 text-muted-foreground">
            Create your account now. Hardware ships Q3 2026 — your data and memories will be ready when your device arrives.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link href="/register" className={buttonVariants({ size: "lg" })}>
              Get Started Free
            </Link>
            <Link href="/pricing" className={buttonVariants({ variant: "outline", size: "lg" })}>
              View Pricing
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
