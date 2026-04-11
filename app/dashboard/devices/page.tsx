"use client";

import { useEffect, useState } from "react";
import { getDevices, unlinkDevice, type Device } from "@/lib/api";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function timeAgo(iso: string | null) {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [unlinking, setUnlinking] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      const data = await getDevices();
      setDevices(data.devices ?? []);
    } catch {
      setError("Could not load devices.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleUnlink(deviceId: string) {
    if (!confirm(`Unlink device ${deviceId}? The device will need to re-pair.`)) return;
    setUnlinking(deviceId);
    try {
      await unlinkDevice(deviceId);
      setDevices((prev) => prev.filter((d) => d.device_id !== deviceId));
    } catch {
      alert("Failed to unlink device.");
    } finally {
      setUnlinking(null);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Devices</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your paired Pixel hardware. Each device links to your account via a 6-digit pairing code.
          </p>
        </div>
        <button
          onClick={load}
          className="rounded-lg border px-3 py-1.5 text-sm hover:bg-muted"
        >
          Refresh
        </button>
      </div>

      {error && (
        <p className="mt-4 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      )}

      {loading ? (
        <div className="mt-12 text-center text-muted-foreground text-sm">Loading…</div>
      ) : devices.length === 0 ? (
        <div className="mt-12 rounded-xl border border-dashed p-10 text-center">
          <p className="text-4xl">📡</p>
          <p className="mt-3 font-semibold">No devices paired yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Power on your Pixel device and enter the 6-digit code shown on its screen.
          </p>
          <div className="mt-6 rounded-lg bg-muted p-4 text-left text-xs text-muted-foreground">
            <p className="font-medium text-foreground mb-1">How pairing works:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>Power on Pixel — it connects to WiFi and shows a 6-digit code</li>
              <li>Open this page and click <strong>Pair new device</strong> (coming soon)</li>
              <li>Enter the code — device is linked to your account</li>
              <li>Pixel stores the permanent token and works without re-pairing</li>
            </ol>
          </div>
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {devices.map((device) => (
            <div
              key={device.id}
              className="flex items-center justify-between rounded-xl border bg-card p-5 shadow-sm"
            >
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-xl">
                  🔌
                </div>
                <div>
                  <p className="font-semibold">{device.model}</p>
                  <p className="text-xs text-muted-foreground font-mono mt-0.5">
                    {device.device_id}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    firmware {device.firmware_version}
                    {" · "}
                    paired {formatDate(device.paired_at)}
                    {" · "}
                    last seen{" "}
                    <span title={device.last_seen_at ?? ""}>{timeAgo(device.last_seen_at)}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleUnlink(device.device_id)}
                disabled={unlinking === device.device_id}
                className="rounded-lg border border-destructive/40 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 disabled:opacity-50"
              >
                {unlinking === device.device_id ? "Unlinking…" : "Unlink"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
