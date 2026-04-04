import Link from "next/link";
import { buttonVariants } from "@/lib/button-variants";
import { cn } from "@/lib/utils";

const PLANS = [
  {
    name: "Pixel Hardware",
    price: "$129",
    period: "one-time",
    description: "The Pixel device itself — everything you need to get started.",
    features: [
      "Pixel AI pendant",
      "USB-C charging cable",
      "Starter neck strap",
      "1 month cloud service included",
      "1 swappable shell (your choice of color)",
    ],
    cta: "Pre-order Now",
    href: "/demo",
    highlight: true,
  },
  {
    name: "Cloud Service",
    price: "$3.99",
    period: "/month",
    description: "Optional subscription for advanced AI features.",
    features: [
      "Unlimited voice conversations",
      "Smart note-taking & PDF export",
      "Active memory system",
      "Real-time translation",
      "Companion web app access",
    ],
    cta: "Learn More",
    href: "/features",
    highlight: false,
  },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      <h1 className="text-center text-4xl font-bold">Simple Pricing</h1>
      <p className="mt-4 text-center text-muted-foreground">
        Buy the hardware once. Cloud service is optional.
      </p>

      <div className="mt-16 grid gap-8 md:grid-cols-2">
        {PLANS.map((p) => (
          <div
            key={p.name}
            className={`flex flex-col rounded-xl border p-8 ${
              p.highlight
                ? "border-primary shadow-lg"
                : "border-border"
            }`}
          >
            <h2 className="text-xl font-bold">{p.name}</h2>
            <div className="mt-4 flex items-baseline gap-1">
              <span className="text-4xl font-bold">{p.price}</span>
              <span className="text-muted-foreground">{p.period}</span>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">{p.description}</p>
            <ul className="mt-6 flex-1 space-y-2">
              {p.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <span className="mt-0.5 text-green-500">&#10003;</span>
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href={p.href}
              className={cn(buttonVariants({ variant: p.highlight ? "default" : "outline" }), "mt-8")}
            >
              {p.cta}
            </Link>
          </div>
        ))}
      </div>

      <p className="mt-12 text-center text-sm text-muted-foreground">
        Kickstarter early-bird pricing coming Q3 2026. Join the waitlist to get
        notified.
      </p>
    </div>
  );
}
