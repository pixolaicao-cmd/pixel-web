import Link from "next/link";
import { buttonVariants } from "@/lib/button-variants";

const FEATURES = [
  {
    icon: "\uD83C\uDFA4",
    title: "Voice Conversations",
    desc: "Talk to Pixel like a friend. It understands Chinese, Norwegian, and English.",
  },
  {
    icon: "\uD83D\uDCDD",
    title: "Smart Notes",
    desc: 'Say "start recording" and Pixel creates structured summaries you can download as PDF.',
  },
  {
    icon: "\uD83E\uDDE0",
    title: "Active Memory",
    desc: "Tell Pixel once and it remembers. Your preferences, schedules, and important details.",
  },
  {
    icon: "\uD83C\uDF0D",
    title: "Real-time Translation",
    desc: "Seamless Chinese-Norwegian-English translation, right from your neck.",
  },
];

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="flex flex-col items-center justify-center px-4 py-24 text-center md:py-36">
        <span className="mb-6 text-6xl">&#x1FA84;</span>
        <h1 className="max-w-3xl text-4xl font-bold leading-tight tracking-tight md:text-6xl">
          Pixel is your first AI friend.
        </h1>
        <p className="mt-6 max-w-xl text-lg text-muted-foreground">
          A tiny AI companion that hangs around your neck. Conversations, notes,
          translation, and memory — completely hands-free.
        </p>
        <div className="mt-8 flex gap-4">
          <Link href="/features" className={buttonVariants({ size: "lg" })}>Learn More</Link>
          <Link href="/pricing" className={buttonVariants({ variant: "outline", size: "lg" })}>See Pricing</Link>
        </div>
      </section>

      {/* Features grid */}
      <section className="border-t bg-muted/30 px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-12 text-center text-3xl font-bold">
            Four things Pixel does best
          </h2>
          <div className="grid gap-8 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="rounded-xl border bg-card p-6 shadow-sm"
              >
                <span className="text-3xl">{f.icon}</span>
                <h3 className="mt-3 text-lg font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 py-20 text-center">
        <h2 className="text-3xl font-bold">Ready to meet Pixel?</h2>
        <p className="mt-4 text-muted-foreground">
          Hardware ships Q3 2026.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link href="/pricing" className={buttonVariants({ size: "lg" })}>See Pricing</Link>
          <Link href="/features" className={buttonVariants({ variant: "outline", size: "lg" })}>Learn More</Link>
        </div>
      </section>
    </>
  );
}
