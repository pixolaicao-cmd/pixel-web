import Link from "next/link";
import { buttonVariants } from "@/lib/button-variants";
import { cn } from "@/lib/utils";

const PLANS = [
  {
    name: "Free",
    price: "Free",
    period: "3 months",
    badge: "Included with hardware",
    description: "Everything you need to get started with Pixel.",
    features: [
      "Voice conversations (limited daily)",
      "Active memory system",
      "Web app access",
      "Multi-language support",
    ],
    missing: [
      "Recording & transcription",
      "Document generation",
    ],
    cta: "Get Started",
    href: "/register",
    highlight: false,
  },
  {
    name: "Basic",
    price: "$5",
    period: "/month",
    badge: null,
    description: "Unlimited conversations and real-time translation.",
    features: [
      "Unlimited voice conversations",
      "Real-time translation",
      "Active memory system",
      "Full web app access",
      "Multi-language support",
    ],
    missing: [
      "Recording & transcription",
      "Document generation",
    ],
    cta: "Choose Basic",
    href: "/register",
    highlight: false,
  },
  {
    name: "Pro",
    price: "$15",
    period: "/month",
    badge: "Most Popular",
    description: "For students and professionals who need meeting & lecture notes.",
    features: [
      "Everything in Basic",
      "15 hours/month recording & transcription",
      "AI document generation",
      "Structured summaries & key points",
      "Download as Markdown",
    ],
    missing: [],
    cta: "Choose Pro",
    href: "/register",
    highlight: true,
  },
  {
    name: "Unlimited",
    price: "$25",
    period: "/month",
    badge: null,
    description: "For creators, travelers, and heavy users.",
    features: [
      "Everything in Pro",
      "Unlimited recording & transcription",
      "Unlimited document generation",
      "Priority processing",
    ],
    missing: [],
    cta: "Choose Unlimited",
    href: "/register",
    highlight: false,
  },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-20">
      {/* Header */}
      <div className="text-center">
        <p className="mb-3 text-sm font-medium text-primary">Pricing</p>
        <h1 className="text-4xl font-bold md:text-5xl">Simple, transparent pricing</h1>
        <p className="mx-auto mt-4 max-w-lg text-muted-foreground">
          Buy the hardware once. The first 3 months of cloud service are included free.
        </p>
      </div>

      {/* Hardware callout */}
      <div className="mx-auto mt-12 max-w-2xl rounded-2xl border border-primary/20 bg-primary/5 px-8 py-6 text-center">
        <p className="text-sm text-muted-foreground">Pixel Hardware</p>
        <p className="mt-1 text-3xl font-bold">$129 <span className="text-base font-normal text-muted-foreground">one-time</span></p>
        <p className="mt-2 text-sm text-muted-foreground">
          Includes the Pixel pendant · USB-C cable · neck strap · <strong>3 months free cloud</strong>
        </p>
        <p className="mt-3 text-xs text-muted-foreground">Hardware ships Q3 2026</p>
      </div>

      {/* Plans */}
      <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {PLANS.map((p) => (
          <div
            key={p.name}
            className={`relative flex flex-col rounded-2xl border p-6 ${
              p.highlight
                ? "border-primary shadow-lg shadow-primary/10"
                : "border-border bg-card"
            }`}
          >
            {p.badge && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground whitespace-nowrap">
                {p.badge}
              </div>
            )}

            <div className="mb-4">
              <h2 className="text-lg font-bold">{p.name}</h2>
              <div className="mt-2 flex items-baseline gap-1">
                <span className="text-3xl font-bold">{p.price}</span>
                <span className="text-sm text-muted-foreground">{p.period}</span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground leading-relaxed">{p.description}</p>
            </div>

            <ul className="flex-1 space-y-2 border-t pt-4">
              {p.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <span className="mt-0.5 shrink-0 text-green-500">✓</span>
                  {f}
                </li>
              ))}
              {p.missing.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-muted-foreground/50 line-through">
                  <span className="mt-0.5 shrink-0">✗</span>
                  {f}
                </li>
              ))}
            </ul>

            <Link
              href={p.href}
              className={cn(
                buttonVariants({ variant: p.highlight ? "default" : "outline", size: "sm" }),
                "mt-6 w-full"
              )}
            >
              {p.cta}
            </Link>
          </div>
        ))}
      </div>

      {/* Footer note */}
      <p className="mt-12 text-center text-sm text-muted-foreground">
        All plans include access to the Pixel web app. Cancel anytime.
        Early-bird pricing available for Kickstarter backers.
      </p>
    </div>
  );
}
