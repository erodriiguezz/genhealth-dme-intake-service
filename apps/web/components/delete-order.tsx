"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";

export function DeleteOrder({ id, label }: { id: string; label: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setPending(true);
    setError(null);
    try {
      await api.deleteOrder(id);
      toast.success("Order deleted");
      router.replace("/orders");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        router.replace("/orders");
        return;
      }
      setError(err instanceof ApiError ? err.message : "Couldn't delete. Try again.");
      setPending(false);
    }
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        className="h-10 border-error-soft bg-card px-3.5 text-destructive hover:bg-error-bg"
        onClick={() => setOpen(true)}
      >
        Delete order
      </Button>
      <AlertDialog open={open} onOpenChange={(o) => !pending && setOpen(o)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this order?</AlertDialogTitle>
            <AlertDialogDescription>
              {label} and its PDF are removed permanently.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {error && (
            <p role="alert" className="text-sm font-medium text-destructive">
              <span aria-hidden>✕ </span>
              {error}
            </p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={pending}>Cancel</AlertDialogCancel>
            <Button
              variant="outline"
              className="border-error-border bg-destructive text-white hover:bg-destructive-hover"
              disabled={pending}
              onClick={confirm}
            >
              {pending && <Loader2 className="animate-spin" aria-hidden />}
              Delete
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
