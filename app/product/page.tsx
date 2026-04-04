const SPECS = [
  { label: "Size", value: "10-15 cm pendant" },
  { label: "Weight", value: "< 50g" },
  { label: "Processor", value: "ESP32-S3 (8MB PSRAM)" },
  { label: "Microphone", value: "INMP441 MEMS" },
  { label: "Speaker", value: "Built-in micro speaker" },
  { label: "Display", value: "OLED status screen" },
  { label: "Connectivity", value: "WiFi + 4G (A7670E)" },
  { label: "Battery", value: "1500-2000 mAh" },
  { label: "Battery Life", value: "8-12 hours" },
  { label: "Storage", value: "MicroSD card slot" },
  { label: "Wake Word", value: "Custom (\"Pixel\")" },
  { label: "Languages", value: "Chinese, Norwegian, English" },
];

export default function ProductPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      <h1 className="text-center text-4xl font-bold">Meet Pixel</h1>
      <p className="mt-4 text-center text-muted-foreground">
        A beautifully simple AI companion designed to hang around your neck.
      </p>

      {/* Product hero */}
      <div className="mt-16 flex flex-col items-center gap-8 md:flex-row">
        <div className="flex h-64 w-64 items-center justify-center rounded-3xl bg-gradient-to-br from-violet-100 to-violet-200 dark:from-violet-900 dark:to-violet-800">
          <span className="text-8xl">&#x1FA84;</span>
        </div>
        <div className="flex-1">
          <h2 className="text-2xl font-bold">Wearable. Personal. Yours.</h2>
          <p className="mt-3 text-muted-foreground">
            Pixel is a pendant-sized AI that hangs from your neck or clips to your
            shirt. No screen to stare at, no phone to pull out. Just speak and
            Pixel responds.
          </p>
          <div className="mt-6 space-y-3">
            <div className="flex items-center gap-2">
              <span>&#x1F3A8;</span>
              <span className="font-medium">Swappable shells</span>
              <span className="text-sm text-muted-foreground">— personalize like a phone case</span>
            </div>
            <div className="flex items-center gap-2">
              <span>&#x1F4CC;</span>
              <span className="font-medium">Brooch mode</span>
              <span className="text-sm text-muted-foreground">— clip it anywhere</span>
            </div>
            <div className="flex items-center gap-2">
              <span>&#x1F310;</span>
              <span className="font-medium">Always connected</span>
              <span className="text-sm text-muted-foreground">— WiFi + 4G fallback</span>
            </div>
          </div>
        </div>
      </div>

      {/* Specs table */}
      <div className="mt-16">
        <h2 className="mb-6 text-2xl font-bold">Technical Specifications</h2>
        <div className="overflow-hidden rounded-xl border">
          {SPECS.map((s, i) => (
            <div
              key={s.label}
              className={`flex justify-between px-6 py-3 text-sm ${
                i % 2 === 0 ? "bg-muted/30" : ""
              }`}
            >
              <span className="font-medium">{s.label}</span>
              <span className="text-muted-foreground">{s.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
