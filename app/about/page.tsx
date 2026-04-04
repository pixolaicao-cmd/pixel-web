const TEAM = [
  {
    role: "Founder",
    desc: "Product vision, business execution, and hands-on operations.",
  },
  {
    role: "Product Design (Cowork)",
    desc: "Industrial design, brand identity, and marketing creative.",
  },
  {
    role: "Tech Lead (Code)",
    desc: "Firmware, cloud backend, web app — all technical implementation.",
  },
  {
    role: "Strategy (Claude)",
    desc: "Market research, competitive analysis, copywriting, and coordination.",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      <h1 className="text-center text-4xl font-bold">About Pixel</h1>
      <p className="mt-4 text-center text-muted-foreground">
        Born in Norway. Built for everyone.
      </p>

      <section className="mt-16">
        <h2 className="text-2xl font-bold">Our Story</h2>
        <div className="mt-4 space-y-4 text-muted-foreground">
          <p>
            We believe AI should feel like a friend, not a tool. Most AI products
            today are screens, apps, and dashboards. We wanted something
            different — something you can wear, talk to, and forget about until
            you need it.
          </p>
          <p>
            Pixel started as a simple idea: what if your AI assistant could hang
            around your neck and just listen when you need it? No phone to pull
            out. No app to open. Just speak.
          </p>
          <p>
            We are a small team based in Norway, combining hardware engineering,
            AI, and design to create the world&apos;s friendliest wearable AI.
          </p>
        </div>
      </section>

      <section className="mt-16">
        <h2 className="mb-8 text-2xl font-bold">The Team</h2>
        <div className="grid gap-6 sm:grid-cols-2">
          {TEAM.map((m) => (
            <div key={m.role} className="rounded-xl border bg-card p-6">
              <h3 className="font-semibold">{m.role}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{m.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-16 rounded-xl bg-muted/30 p-8 text-center">
        <h2 className="text-2xl font-bold">Our Mission</h2>
        <p className="mt-4 text-lg text-muted-foreground">
          Make AI personal, warm, and hands-free — for everyone.
        </p>
      </section>
    </div>
  );
}
