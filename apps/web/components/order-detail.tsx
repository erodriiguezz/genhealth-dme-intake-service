"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { DeleteOrder } from "@/components/delete-order";
import { OrderForm } from "@/components/order-form";
import { StatusBadge } from "@/components/status-badge";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api, fieldErrorsFrom } from "@/lib/api";
import type { Order, OrderValues } from "@/lib/api-types";
import { patientName } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

export function OrderBanner({ order }: { order: Order }) {
  const errors = order.issues.filter((i) => i.severity === "error").length;
  if (order.status === "ready") {
    return (
      <p role="status" className="rounded-lg bg-ready-bg px-4 py-2.5 text-sm font-medium text-ready-fg">
        <span aria-hidden>✓ </span>All fields verified
      </p>
    );
  }
  return (
    <p role="status" className="rounded-lg bg-review-bg px-4 py-2.5 text-sm font-medium text-review-fg">
      <span aria-hidden>⚠ </span>
      {errors > 0
        ? `${errors} ${errors === 1 ? "error" : "errors"} must be fixed before this order is ready.`
        : "This order needs review."}
    </p>
  );
}

export function NotFoundCard() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border bg-card px-6 py-14 text-center">
      <h1 className="font-title text-[28px]">Order not found</h1>
      <p className="text-muted-foreground">It may have been deleted, or it belongs to another account.</p>
      <Link href="/orders" className={cn(buttonVariants({ variant: "outline" }), "mt-2 h-10 px-4")}>
        Back to orders
      </Link>
    </div>
  );
}

export function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: order, error, loading, retry, setData } = useApi(`order:${id}`, () => api.getOrder(id));
  const [saveError, setSaveError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<ReturnType<typeof fieldErrorsFrom>>({});

  async function save(values: Partial<OrderValues>) {
    setSaveError(null);
    setFieldErrors({});
    try {
      setData(await api.updateOrder(id, values));
      toast.success("Changes saved");
    } catch (err) {
      const fe = fieldErrorsFrom(err);
      setFieldErrors(fe);
      setSaveError(Object.keys(fe).length ? "Fix the highlighted fields and save again." : err instanceof ApiError ? err.message : "Couldn't save. Try again.");
    }
  }

  return (
    <>
      <div>
        <Link href="/orders" className="text-primary hover:text-primary-hover hover:underline">
          ← Orders
        </Link>
      </div>
      {error?.status === 404 ? (
        <NotFoundCard />
      ) : error ? (
        <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border border-error-border bg-error-bg px-4 py-3 text-destructive">
          Couldn&apos;t load this order. {error.message}
          <button type="button" onClick={retry} className="font-semibold underline">
            Retry
          </button>
        </div>
      ) : loading || !order ? (
        <div role="status" aria-busy="true" aria-label="Loading order" className="flex flex-col gap-4 rounded-xl border bg-card p-6">
          <Skeleton className="h-8 w-1/2" />
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : (
        <section className="flex flex-col gap-5 rounded-xl border bg-card p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="font-title text-[26px] leading-tight sm:text-[30px]">
              {patientName(order) ?? "Unnamed patient"}
            </h1>
            <StatusBadge status={order.status} />
          </div>
          <OrderBanner order={order} />
          <OrderForm order={order} onSubmit={save} submitLabel="Save changes"
            formError={saveError}
            fieldErrors={fieldErrors}
            leading={<DeleteOrder id={order.id} label={patientName(order) ?? "This order"} />}
          />
        </section>
      )}
    </>
  );
}
