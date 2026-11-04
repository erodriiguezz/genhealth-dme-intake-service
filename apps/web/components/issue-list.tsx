import { AlertTriangle, X } from "lucide-react";
import type { Issue, OrderField } from "@/lib/api-types";

export const issueId = (field: OrderField, i: number) => `issue-${field}-${i}`;

export function PageChip({ page }: { page: number | null }) {
  if (page == null) return null;
  return (
    <span className="inline-flex h-[22px] shrink-0 items-center rounded-full border bg-background px-1.5 font-sans text-[11px] font-medium text-primary">
      p.{page}
    </span>
  );
}

/** Issues for one field. Errors are red with an X, warnings amber with a triangle. */
export function FieldIssues({ field, issues }: { field: OrderField; issues: Issue[] }) {
  if (issues.length === 0) return null;
  return (
    <ul className="flex flex-col gap-1">
      {issues.map((issue, i) => {
        const error = issue.severity === "error";
        return (
          <li
            key={`${issue.code}-${i}`}
            id={issueId(field, i)}
            data-severity={issue.severity}
            className={`flex items-start gap-1.5 text-[13px] ${error ? "font-medium text-destructive" : "text-review-fg"}`}
          >
            {error ? (
              <X className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            ) : (
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            )}
            <span>
              <span className="sr-only">{error ? "Error: " : "Warning: "}</span>
              {issue.message}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
