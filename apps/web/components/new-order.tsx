"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { OrderForm } from "@/components/order-form";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { UploadDropzone } from "@/components/upload-dropzone";
import { ApiError, api } from "@/lib/api";
import type { OrderValues } from "@/lib/api-types";

export function NewOrder() {
  const router = useRouter();
  const initial = useSearchParams().get("tab") === "manual" ? "manual" : "upload";
  const [tab, setTab] = useState<string>(initial);
  const [error, setError] = useState<string | null>(null);
  const [formVersion, setFormVersion] = useState(0);

  async function create(values: Partial<OrderValues>) {
    setError(null);
    try {
      const order = await api.createOrder(values);
      // The page stays mounted (hidden) after navigating, so clear the draft.
      setFormVersion((v) => v + 1);
      router.push(`/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create the order. Try again.");
    }
  }

  return (
    <Tabs value={tab} onValueChange={(v) => setTab(String(v))} className="gap-4">
      <TabsList aria-label="Create order" className="h-10 self-start">
        <TabsTrigger value="upload" className="px-4">Upload PDF</TabsTrigger>
        <TabsTrigger value="manual" className="px-4">Enter manually</TabsTrigger>
      </TabsList>
      <TabsContent value="upload">
        <UploadDropzone />
      </TabsContent>
      <TabsContent value="manual">
        <section className="rounded-xl border bg-card p-5 sm:p-6">
          <p className="mb-5 text-sm text-muted-foreground">
            Leave a field empty if it isn&apos;t known. It will be flagged for review.
          </p>
          <OrderForm key={formVersion} onSubmit={create} submitLabel="Create order" formError={error} />
        </section>
      </TabsContent>
    </Tabs>
  );
}
