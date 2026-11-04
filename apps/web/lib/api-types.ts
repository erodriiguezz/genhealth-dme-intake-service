// Hand-written from docs/architecture/api.md. Replace with `pnpm gen:api` output once the API is merged.

export type OrderStatus = "needs_review" | "ready";
export type OrderField =
  | "patient_first_name"
  | "patient_last_name"
  | "patient_dob"
  | "provider_name"
  | "provider_npi";

export const ORDER_FIELDS: OrderField[] = [
  "patient_first_name",
  "patient_last_name",
  "patient_dob",
  "provider_name",
  "provider_npi",
];

export type Issue = {
  field: OrderField;
  code: string;
  severity: "error" | "warning";
  message: string;
  source: "validation" | "extraction";
};

export type FieldEvidence = {
  raw: string | null;
  evidence: string | null;
  page: number | null;
  grounded: boolean;
};

export type ProviderCandidate = {
  name: string;
  role: string;
  npi: string | null;
  page: number | null;
};

export type Extraction = {
  model: string;
  latency_ms: number;
  fields: Partial<Record<OrderField, FieldEvidence>>;
  provider_candidates: ProviderCandidate[];
};

export type DocumentMeta = {
  id: string;
  filename: string;
  page_count: number;
  size_bytes: number;
};

export type OrderValues = {
  patient_first_name: string | null;
  patient_last_name: string | null;
  patient_dob: string | null;
  provider_name: string | null;
  provider_npi: string | null;
};

export type OrderSummary = OrderValues & {
  id: string;
  status: OrderStatus;
  issues: Issue[];
  document: DocumentMeta | null;
  created_at: string;
  updated_at: string;
};

export type Order = OrderSummary & { extraction: Extraction | null };

export type OrderList = { items: OrderSummary[]; total: number };

export type User = { id: string; email: string; created_at: string };
export type TokenResponse = { access_token: string; token_type: "bearer"; expires_in: number };

export type ErrorEnvelope = {
  error: { code: string; message: string; details: unknown };
};
