"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { getStoredUser, logout } from "@/lib/api";

export default function SettingsPage() {
  const router = useRouter();
  const user = getStoredUser();

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold">Settings</h1>

      <div className="mt-8 space-y-6">
        <div className="rounded-xl border bg-card p-6">
          <h2 className="font-semibold">Account</h2>
          <div className="mt-3 space-y-2 text-sm">
            <p><span className="text-muted-foreground">Name:</span> {user?.name}</p>
            <p><span className="text-muted-foreground">Email:</span> {user?.email}</p>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-6">
          <h2 className="font-semibold">Device</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            No Pixel device connected. Device binding will be available when hardware ships.
          </p>
        </div>

        <div className="rounded-xl border bg-card p-6">
          <h2 className="font-semibold">Subscription</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Free tier — upgrade to Pixel Cloud for unlimited features.
          </p>
        </div>

        <div className="rounded-xl border border-red-200 bg-card p-6">
          <h2 className="font-semibold text-red-600">Danger Zone</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign out of your account.
          </p>
          <Button
            variant="destructive"
            className="mt-4"
            onClick={() => { logout(); router.push("/"); }}
          >
            Sign Out
          </Button>
        </div>
      </div>
    </div>
  );
}
