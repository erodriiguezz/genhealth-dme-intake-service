"use client";

import { FileText } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { OrderStatus, OrderSummary } from "@/lib/api-types";
import { patientName, receivedLabel } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

const FILTERS: { label: string; value: OrderStatus | null }[] = [
  { label: "All", value: null },
  { label: "Needs review", value: "needs_review" },
  { label: "Ready", value: "ready" },
];

const HEADERS = ["Patient", "DOB", "Ordering provider", "NPI", "Status", "Received"];

function NotFound() {
  return <span className="text-muted-foreground">Not found</span>;
}

export function OrdersView() {
  const params = useSearchParams();
  const raw = params.get("status");
  const status: OrderStatus | null = raw === "needs_review" || raw === "ready" ? raw : null;
  const { data, error, loading, retry } = useApi(`orders:${status}`, () =>
    api.listOrders(status ?? undefined),
  );

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-title text-[30px] leading-tight">Orders</h1>
        <div className="flex flex-wrap gap-2">
          <Link href="/orders/new?tab=manual" className={cn(buttonVariants({ variant: "outline" }), "h-10 px-3.5")}>
            New order
          </Link>
          <Link href="/orders/new" className={cn(buttonVariants(), "h-10 px-3.5 font-semibold")}>
            Upload PDF
          </Link>
        </div>
      </div>

      <nav aria-label="Filter by status" className="flex flex-wrap gap-1">
        {FILTERS.map((f) => {
          const on = f.value === status;
          return (
            <Link
              key={f.label}
              href={f.value ? `/orders?status=${f.value}` : "/orders"}
              aria-current={on ? "page" : undefined}
              className={cn(
                "inline-flex h-[34px] items-center rounded-full border px-3 text-sm transition-colors",
                on
                  ? "border-primary bg-primary font-semibold text-primary-foreground"
                  : "bg-card text-foreground hover:bg-card/60",
              )}
            >
              {f.label}
            </Link>
          );
        })}
      </nav>

      {error ? (
        <Alert variant="destructive" className="bg-error-bg">
          <AlertTitle>Couldn&apos;t load orders</AlertTitle>
          <AlertDescription className="flex flex-wrap items-center gap-3">
            {error.message}
            <Button variant="outline" size="sm" onClick={retry}>
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      ) : loading ? (
        <div aria-busy="true" aria-label="Loading orders" role="status" className="flex flex-col gap-2 rounded-xl border bg-card p-4">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      ) : data && data.items.length === 0 ? (
        <EmptyState filtered={status !== null} />
      ) : (
        <OrdersTable items={data?.items ?? []} />
      )}
    </>
  );
}

function EmptyState({ filtered }: { filtered: boolean }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border bg-card px-6 py-14 text-center">
      <FileText className="size-9 text-muted-foreground" strokeWidth={1.5} aria-hidden />
      <h2 className="text-lg font-semibold">{filtered ? "No orders match this filter" : "No orders yet"}</h2>
      <p className="max-w-sm text-muted-foreground">
        {filtered
          ? "Try another status, or view all orders."
          : "Upload a faxed order PDF and we'll pull out the patient and provider details."}
      </p>
      {!filtered && (
        <div className="flex flex-wrap justify-center gap-2">
          <Link href="/orders/new" className={cn(buttonVariants(), "h-10 px-4 font-semibold")}>
            Upload PDF
          </Link>
          <Link href="/orders/new?tab=manual" className={cn(buttonVariants({ variant: "outline" }), "h-10 px-4")}>
            Enter manually
          </Link>
        </div>
      )}
    </div>
  );
}

function OrdersTable({ items }: { items: OrderSummary[] }) {
  const router = useRouter();
  return (
    <div className="overflow-x-auto rounded-xl border bg-card">
      <table className="w-full min-w-[760px] border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
            {HEADERS.map((h) => (
              <th key={h} scope="col" className="px-4 py-3 font-semibold">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((o) => {
            const name = patientName(o);
            return (
              <tr
                key={o.id}
                onClick={() => router.push(`/orders/${o.id}`)}
                className="cursor-pointer border-t hover:bg-muted/60"
              >
                <td className="px-4 py-3 font-medium">
                  <Link href={`/orders/${o.id}`} className="text-primary hover:text-primary-hover hover:underline" onClick={(e) => e.stopPropagation()}>
                    {name ?? "Unnamed patient"}
                  </Link>
                </td>
                <td className="whitespace-nowrap px-4 py-3 font-mono text-[13px]">{o.patient_dob ?? <NotFound />}</td>
                <td className="px-4 py-3">{o.provider_name ?? <NotFound />}</td>
                <td className="whitespace-nowrap px-4 py-3 font-mono text-[13px]">{o.provider_npi ?? <NotFound />}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={o.status} />
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">{receivedLabel(o.created_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
