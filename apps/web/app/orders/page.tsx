import type { Metadata } from "next";
import { Suspense } from "react";
import { PageShell } from "@/components/app-header";
import { OrdersView } from "@/components/orders-table";

export const metadata: Metadata = { title: "Orders · DME Intake" };

export default function Page() {
  return (
    <PageShell>
      <Suspense fallback={<p role="status" className="text-muted-foreground">Loading…</p>}>
        <OrdersView />
      </Suspense>
    </PageShell>
  );
}
