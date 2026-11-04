import { AlertTriangle, Check } from "lucide-react";
import type { OrderStatus } from "@/lib/api-types";

export function StatusBadge({ status }: { status: OrderStatus }) {
  const ready = status === "ready";
  const Icon = ready ? Check : AlertTriangle;
  return (
    <span
      data-testid="status-badge"
      className={`inline-flex h-[26px] items-center gap-1 whitespace-nowrap rounded-full px-2.5 text-xs font-semibold ${
        ready ? "bg-ready-bg text-ready-fg" : "bg-review-bg text-review-fg"
      }`}
    >
      <Icon className="size-3.5" aria-hidden />
      {ready ? "Ready" : "Needs review"}
    </span>
  );
}
