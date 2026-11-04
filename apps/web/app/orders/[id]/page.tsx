import type { Metadata } from "next";
import { Suspense } from "react";
import { PageShell } from "@/components/app-header";
import { OrderDetail } from "@/components/order-detail";

export const metadata: Metadata = { title: "Review order · DME Intake" };

export default function Page() {
  return (
    <PageShell>
      <Suspense fallback={<p role="status" className="text-muted-foreground">Loading…</p>}>
        <OrderDetail />
      </Suspense>
    </PageShell>
  );
}
