"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useEffect, useId } from "react";
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
  patient_first_name: z.string().max(200, "Too long"),
  patient_last_name: z.string().max(200, "Too long"),
  patient_dob: z.string().refine((v) => v === "" || /^\d{4}-\d{2}-\d{2}$/.test(v), "Use the format YYYY-MM-DD"),
  provider_name: z.string().max(300, "Too long"),
  provider_npi: z.string().max(40, "Too long"),
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
  /** Server-side 422 messages keyed by field. */
  fieldErrors?: Partial<Record<OrderField, string>>;
};

export function OrderForm({ order, onSubmit, submitLabel, leading, formError, fieldErrors = {} }: Props) {
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

  // Pages stay mounted (hidden) after navigation, so ids must be unique per form instance.
  const uid = useId();
  const idOf = (f: string) => `${uid}-${f}`;
  const issuesFor = (f: OrderField) => order?.issues.filter((i) => i.field === f) ?? [];
  const candidates = order?.extraction?.provider_candidates ?? [];

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
        const shapeError = errors[f]?.message ?? fieldErrors[f];
        const hasError = issues.some((i) => i.severity === "error") || Boolean(shapeError);
        const evidence = order?.extraction?.fields[f];
        const showEvidence = evidence?.evidence && !dirtyFields[f];
        // Dates are normalised by the server, so only compare the free-text fields.
        const edited = f !== "patient_dob" && evidence?.raw != null && (order?.[f] ?? "").replace(/\s/g, "").toLowerCase() !== evidence.raw.replace(/\s/g, "").toLowerCase();
        const describedBy = [
          ...issues.map((_, i) => issueId(f, i, uid)),
          shapeError ? idOf(`shape-${f}`) : null,
          showEvidence ? idOf(`evidence-${f}`) : null,
        ].filter(Boolean).join(" ");
        const otherCandidates = f === "provider_name"
          ? candidates.filter((c) => c.name !== order?.provider_name)
          : [];
        return (
          <div
            key={f}
            className={cn("flex flex-col gap-1.5", hasError && "-ml-[15px] border-l-[3px] border-error-border pl-3")}
          >
            <Label htmlFor={idOf(f)}>{meta.label}</Label>
            <Input
              id={idOf(f)}
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
                hasError && "border-2 border-error-border",
              )}
            />
            {shapeError && (
              <p id={idOf(`shape-${f}`)} className="text-[13px] font-medium text-destructive">
                <span aria-hidden>✕ </span>
                {shapeError}
              </p>
            )}
            <FieldIssues field={f} issues={issues} idPrefix={uid} />
            {showEvidence && (
              <p id={idOf(`evidence-${f}`)} data-testid={`evidence-${f}`} className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>
                  <span className={edited ? "" : "sr-only"}>{edited ? "Originally read as: " : "Evidence: "}</span>
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
        <p role="alert" className="rounded-lg border border-error-border bg-error-bg px-3 py-2 text-sm font-medium text-destructive">
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
