"use client";

import { useEffect, useState } from "react";

type State = "loading" | "ok" | "degraded" | "unreachable";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const LABEL: Record<State, string> = {
  loading: "API: checking…",
  ok: "API: ok",
  degraded: "API: degraded (db down)",
  unreachable: "API: unreachable",
};

const DOT: Record<State, string> = {
  loading: "bg-muted-foreground animate-pulse",
  ok: "bg-ready-fg",
  degraded: "bg-review-fg",
  unreachable: "bg-destructive",
};

export function ApiStatus() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    fetch(`${API_URL}/health`, { signal: controller.signal })
      .then((res) => {
        if (active) setState(res.status === 200 ? "ok" : res.status === 503 ? "degraded" : "unreachable");
      })
      .catch(() => active && setState("unreachable"))
      .finally(() => clearTimeout(timer));
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, []);

  return (
    <p
      role="status"
      className="inline-flex items-center gap-2 rounded-md border bg-card px-3 py-2 text-sm font-medium"
    >
      <span aria-hidden className={`size-2.5 rounded-full ${DOT[state]}`} />
      {LABEL[state]}
    </p>
  );
}
