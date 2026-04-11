"use client";

/**
 * /auth/callback — Google OAuth 回调落地页
 *
 * 后端 /api/users/google/callback 把 token、email、name 放在 URL 参数里重定向到这里。
 * 这个页面把参数写入 localStorage，然后跳到 dashboard。
 */

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { consumeOAuthCallback } from "@/lib/api";
import { Suspense } from "react";

function CallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const error  = params.get("error");

  useEffect(() => {
    if (error) {
      router.replace(`/login?error=${error}`);
      return;
    }
    const ok = consumeOAuthCallback();
    router.replace(ok ? "/dashboard" : "/login?error=oauth_failed");
  }, [error, router]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center space-y-3">
        <span className="text-4xl">🔮</span>
        <p className="text-muted-foreground text-sm">Signing you in…</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[60vh] items-center justify-center">
          <p className="text-muted-foreground text-sm">Loading…</p>
        </div>
      }
    >
      <CallbackInner />
    </Suspense>
  );
}
