"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { FieldIssues, PageChip, issueId } from "@/components/issue-list";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Order, OrderField, OrderValues } from "@/lib/api-types";
import { ORDER_FIELDS } from "@/lib/api-types";
import { cn } from "@/lib/utils";

// Shape only. The server decides what is valid and what the status is.
const schema = z.object({
  patient_first_name: z.string().max(100, "Too long"),
  patient_last_name: z.string().max(100, "Too long"),
  patient_dob: z.string().refine((v) => v === "" || /^\d{4}-\d{2}-\d{2}$/.test(v), "Use the format YYYY-MM-DD"),
  provider_name: z.string().max(200, "Too long"),
  provider_npi: z.string().max(20, "Too long"),
});
type FormValues = z.infer<typeof schema>;

const FIELD_META: Record<OrderField, { label: string; placeholder?: string; mono?: boolean; numeric?: boolean; narrow?: boolean; autoComplete?: string }> = {
  patient_first_name: { label: "Patient first name" },
  patient_last_name: { label: "Patient last name" },
  patient_dob: { label: "Date of birth", placeholder: "YYYY-MM-DD", mono: true, narrow: true },
  provider_name: { label: "Ordering provider name" },
  provider_npi: { label: "Ordering provider NPI", mono: true, numeric: true, narrow: true },
};

const toForm = (o?: Order): FormValues => ({
  patient_first_name: o?.patient_first_name ?? "",
  patient_last_name: o?.patient_last_name ?? "",
  patient_dob: o?.patient_dob ?? "",
  provider_name: o?.provider_name ?? "",
  provider_npi: o?.provider_npi ?? "",
});

type Props = {
  order?: Order;
  /** Called with only the fields the user changed (edit) or all filled fields (create). */
  onSubmit: (values: Partial<OrderValues>) => Promise<void>;
  submitLabel: string;
  /** Rendered on the left of the action row, e.g. the delete button. */
  leading?: React.ReactNode;
  formError?: string | null;
};

export function OrderForm({ order, onSubmit, submitLabel, leading, formError }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, dirtyFields, isSubmitting, isDirty },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: toForm(order) });

  // Re-render from the server's response after every save.
  useEffect(() => {
    reset(toForm(order));
  }, [order, reset]);

  const issuesFor = (f: OrderField) => order?.issues.filter((i) => i.field === f) ?? [];
  const candidates = order?.extraction?.provider_candidates ?? [];
  const hasCandidateIssue = order?.issues.some((i) => i.code === "provider.multiple_candidates") ?? false;

  async function submit(values: FormValues) {
    const payload: Partial<OrderValues> = {};
    for (const f of ORDER_FIELDS) {
      if (order && !dirtyFields[f]) continue;
      const v = values[f].trim();
      if (!order && v === "") continue;
      payload[f] = v === "" ? null : v;
    }
    await onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-5" noValidate>
      {ORDER_FIELDS.map((f) => {
        const meta = FIELD_META[f];
        const issues = issuesFor(f);
        const hasError = issues.some((i) => i.severity === "error") || Boolean(errors[f]);
        const evidence = order?.extraction?.fields[f];
        const showEvidence = evidence?.evidence && !dirtyFields[f];
        const describedBy = [
          ...issues.map((_, i) => issueId(f, i)),
          errors[f] ? `shape-${f}` : null,
          showEvidence ? `evidence-${f}` : null,
        ].filter(Boolean).join(" ");
        const otherCandidates = f === "provider_name" && !hasCandidateIssue
          ? candidates.filter((c) => c.name !== order?.provider_name)
          : [];
        return (
          <div
            key={f}
            className={cn("flex flex-col gap-1.5", hasError && "border-l-[3px] border-[#C9192E] pl-3")}
          >
            <Label htmlFor={f}>{meta.label}</Label>
            <Input
              id={f}
              {...register(f)}
              placeholder={meta.placeholder}
              inputMode={meta.numeric ? "numeric" : undefined}
              autoComplete="off"
              aria-invalid={hasError ? true : undefined}
              aria-describedby={describedBy || undefined}
              className={cn(
                "h-10 px-3",
                meta.mono && "font-mono",
                meta.narrow && "sm:max-w-[240px]",
                hasError && "border-2 border-[#C9192E]",
              )}
            />
            {errors[f] && (
              <p id={`shape-${f}`} className="text-[13px] font-medium text-destructive">
                <span aria-hidden>✕ </span>
                {errors[f]?.message}
              </p>
            )}
            <FieldIssues field={f} issues={issues} />
            {showEvidence && (
              <p id={`evidence-${f}`} data-testid={`evidence-${f}`} className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>
                  <span className="sr-only">Evidence: </span>
                  <q className="font-mono">{evidence.evidence}</q>
                </span>
                <PageChip page={evidence.page} />
              </p>
            )}
            {otherCandidates.length > 0 && (
              <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                Also on the document:
                {otherCandidates.map((c) => (
                  <span key={`${c.name}-${c.page}`} className="inline-flex items-center gap-1.5">
                    {c.name}, {c.role} <PageChip page={c.page} />
                  </span>
                ))}
              </p>
            )}
          </div>
        );
      })}

      {formError && (
        <p role="alert" className="rounded-lg border border-[#C9192E] bg-error-bg px-3 py-2 text-sm font-medium text-destructive">
          <span aria-hidden>✕ </span>
          {formError}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
        <div>{leading}</div>
        <Button type="submit" disabled={isSubmitting || (Boolean(order) && !isDirty)} className="h-10 px-[18px] font-semibold">
          {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
