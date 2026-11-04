import type { OrderValues } from "./api-types";

export function patientName(o: Pick<OrderValues, "patient_first_name" | "patient_last_name">) {
  const { patient_first_name: first, patient_last_name: last } = o;
  if (first && last) return `${last}, ${first}`;
  return last ?? first ?? null;
}

export function receivedLabel(iso: string, now = new Date()) {
  const d = new Date(iso);
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  const day = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((day(now) - day(d)) / 86_400_000);
  if (diff === 0) return `Today ${time}`;
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
}

export function formatBytes(n: number) {
  return n >= 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`;
}
