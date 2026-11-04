import { expect, test as base, type Page, type Route } from "@playwright/test";

export const API_URL = process.env.API_URL ?? "http://localhost:8002";
export const REAL_API = process.env.E2E_REAL_API === "1";

type Issue = { field: string; code: string; severity: "error" | "warning"; message: string; source: "validation" | "extraction" };
export type StubOrder = {
  id: string;
  status: "needs_review" | "ready";
  patient_first_name: string | null;
  patient_last_name: string | null;
  patient_dob: string | null;
  provider_name: string | null;
  provider_npi: string | null;
  issues: Issue[];
  extraction: unknown;
  document: unknown;
  created_at: string;
  updated_at: string;
};

const FIELDS = ["patient_first_name", "patient_last_name", "patient_dob", "provider_name", "provider_npi"] as const;
type Field = (typeof FIELDS)[number];

export function npiChecksumOk(n: string) {
  if (!/^\d{10}$/.test(n)) return false;
  const digits = ("80840" + n.slice(0, 9)).split("").map(Number);
  let sum = 0;
  for (let i = digits.length - 1, k = 0; i >= 0; i--, k++) {
    let x = digits[i];
    if (k % 2 === 0) {
      x *= 2;
      if (x > 9) x -= 9;
    }
    sum += x;
  }
  return (10 - (sum % 10)) % 10 === Number(n[9]);
}

const LABEL: Record<Field, string> = {
  patient_first_name: "Patient first name",
  patient_last_name: "Patient last name",
  patient_dob: "Date of birth",
  provider_name: "Provider name",
  provider_npi: "Provider NPI",
};

/** Mirrors the server's re-validation closely enough for the UI specs. */
function revalidate(o: StubOrder, kept: Issue[]) {
  const issues: Issue[] = [...kept];
  for (const f of FIELDS) {
    if (!o[f]) {
      issues.push({ field: f, code: `${f}.not_found`, severity: "error", message: `${LABEL[f]} was not found. Enter it from the source document.`, source: "validation" });
    }
  }
  if (o.provider_npi && !/^[12]/.test(o.provider_npi)) {
    issues.push({ field: "provider_npi", code: "npi.prefix", severity: "error", message: "An NPI starts with 1 or 2.", source: "validation" });
  }
  if (o.provider_npi && !npiChecksumOk(o.provider_npi)) {
    issues.push({ field: "provider_npi", code: "npi.checksum_failed", severity: "error", message: "Fails the NPI checksum. This isn't a valid NPI as written.", source: "validation" });
  }
  if (o.patient_dob) {
    const age = (Date.now() - new Date(o.patient_dob).getTime()) / (365.25 * 86_400_000);
    if (age > 120) issues.push({ field: "patient_dob", code: "dob.age_over_120", severity: "warning", message: `Patient would be ${Math.floor(age)} years old. Check the date.`, source: "validation" });
  }
  o.issues = issues;
  o.status = issues.some((i) => i.severity === "error") ? "needs_review" : "ready";
}

export function benchmarkOrder(id = "11111111-1111-4111-8111-111111111111"): StubOrder {
  const o: StubOrder = {
    id,
    status: "needs_review",
    patient_first_name: "Marie",
    patient_last_name: "Curie",
    patient_dob: "1900-12-05",
    provider_name: "Arjun Raj D.P.M",
    provider_npi: "9182734556",
    issues: [],
    extraction: {
      model: "fake",
      latency_ms: 12,
      fields: {
        patient_first_name: { raw: "Marie", evidence: "Marie Curie", page: 1, grounded: true },
        patient_last_name: { raw: "Curie", evidence: "Marie Curie", page: 1, grounded: true },
        patient_dob: { raw: "12/05/1900", evidence: "Patient Date of Birth 12/05/1900", page: 1, grounded: true },
        provider_name: { raw: "Arjun Raj D.P.M", evidence: "Prescriber Name and Address Arjun Raj D.P.M", page: 1, grounded: true },
        provider_npi: { raw: "9182734556", evidence: "Prescriber NPI: 9182734556", page: 1, grounded: true },
      },
      provider_candidates: [
        { name: "Arjun Raj D.P.M", role: "prescriber", npi: "9182734556", page: 1 },
        { name: "Gregory House MD", role: "referring physician", npi: null, page: 2 },
      ],
    },
    document: { id: "a0b2c3d4", filename: "DME Patient Demo Document CPAP.fax.pdf", page_count: 4, size_bytes: 1992294 },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  revalidate(o, [
    { field: "provider_name", code: "provider.multiple_candidates", severity: "warning", message: "More than one provider appears on this document. Confirm the ordering provider.", source: "extraction" },
  ]);
  return o;
}

export function manualOrder(id: string, v: Partial<Record<Field, string>>, created = new Date().toISOString()): StubOrder {
  const o: StubOrder = {
    id, status: "needs_review", patient_first_name: null, patient_last_name: null, patient_dob: null, provider_name: null, provider_npi: null,
    issues: [], extraction: null, document: null, created_at: created, updated_at: created, ...v,
  };
  revalidate(o, []);
  return o;
}

export class Stub {
  orders: StubOrder[] = [];
  users = new Map<string, string>();
  delayMs = 0;
  listStatus = 0;
  extractCalls = 0;
  private seq = 100;

  seed(...o: StubOrder[]) {
    this.orders.push(...o);
  }

  private cors(extra: Record<string, string> = {}) {
    return {
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "authorization,content-type",
      "access-control-allow-methods": "GET,POST,PATCH,DELETE,OPTIONS",
      ...extra,
    };
  }

  private err(route: Route, status: number, code: string, message: string) {
    return route.fulfill({ status, headers: this.cors(), json: { error: { code, message, details: null } } });
  }

  async handle(route: Route) {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    const method = req.method();
    if (method === "OPTIONS") return route.fulfill({ status: 204, headers: this.cors() });
    if (this.delayMs) await new Promise((r) => setTimeout(r, this.delayMs));
    const json = (status: number, body: unknown) => route.fulfill({ status, headers: this.cors(), json: body });

    if (path === "/auth/register" && method === "POST") {
      const { email, password } = req.postDataJSON();
      if (this.users.has(email)) return this.err(route, 409, "email_taken", "That email is already registered.");
      if (!password || password.length < 8) return this.err(route, 422, "validation_error", "Password too short.");
      this.users.set(email, password);
      return json(201, { id: "u1", email, created_at: new Date().toISOString() });
    }
    if (path === "/auth/login" && method === "POST") {
      const form = new URLSearchParams(req.postData() ?? "");
      const email = form.get("username") ?? "";
      if (this.users.get(email) !== form.get("password")) return this.err(route, 401, "invalid_credentials", "Incorrect email or password.");
      return json(200, { access_token: `tok:${email}`, token_type: "bearer", expires_in: 3600 });
    }

    const auth = req.headers()["authorization"] ?? "";
    if (!auth.startsWith("Bearer tok:")) return this.err(route, 401, "not_authenticated", "Not authenticated.");
    const email = auth.slice("Bearer tok:".length);

    if (path === "/auth/me") return json(200, { id: "u1", email, created_at: new Date().toISOString() });

    if (path === "/orders" && method === "GET") {
      if (this.listStatus) return this.err(route, this.listStatus, "internal_error", "The server had a problem.");
      const status = url.searchParams.get("status");
      const items = this.orders
        .filter((o) => !status || o.status === status)
        .map(({ extraction: _e, ...rest }) => rest);
      return json(200, { items, total: items.length });
    }
    if (path === "/orders" && method === "POST") {
      const body = req.postDataJSON();
      const o = manualOrder(`00000000-0000-4000-8000-${String(++this.seq).padStart(12, "0")}`, body);
      this.orders.unshift(o);
      return json(201, o);
    }
    if (path === "/orders/extract" && method === "POST") {
      this.extractCalls++;
      const body = req.postData() ?? "";
      const filename = /filename="([^"]*)"/.exec(body)?.[1] ?? "";
      if (filename.includes("503")) return this.err(route, 503, "extraction_unavailable", "Extraction is not configured.");
      if (filename.includes("502") && this.extractCalls === 1) return this.err(route, 502, "extraction_failed", "Extraction failed.");
      if (filename.includes("slow")) await new Promise((r) => setTimeout(r, 2500));
      const o = benchmarkOrder(`22222222-2222-4222-8222-${String(++this.seq).padStart(12, "0")}`);
      this.orders.unshift(o);
      return json(201, o);
    }

    const m = /^\/orders\/([^/]+)$/.exec(path);
    if (m) {
      const idx = this.orders.findIndex((o) => o.id === m[1]);
      if (idx < 0) return this.err(route, 404, "order_not_found", "Order not found.");
      const o = this.orders[idx];
      if (method === "GET") return json(200, o);
      if (method === "DELETE") {
        this.orders.splice(idx, 1);
        return route.fulfill({ status: 204, headers: this.cors() });
      }
      if (method === "PATCH") {
        const body = req.postDataJSON() as Partial<Record<Field, string | null>>;
        const edited = Object.keys(body);
        for (const f of FIELDS) if (f in body) o[f] = body[f] ?? null;
        revalidate(o, o.issues.filter((i) => i.source === "extraction" && !edited.includes(i.field)));
        o.updated_at = new Date().toISOString();
        return json(200, o);
      }
    }
    return this.err(route, 404, "not_found", "Not found.");
  }
}

type Fixtures = { stub: Stub; signedIn: Page };

/** `stub` intercepts the API with route handlers; with E2E_REAL_API=1 it is inert and the real API answers. */
export const test = base.extend<Fixtures>({
  stub: async ({ page }, use) => {
    const stub = new Stub();
    if (!REAL_API) await page.route(`${API_URL}/**`, (route) => stub.handle(route));
    await use(stub);
  },
  signedIn: async ({ page, stub }, use) => {
    const email = `qa-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
    const password = "correct-horse-9";
    if (!REAL_API) stub.users.set(email, password);
    else await page.request.post(`${API_URL}/auth/register`, { data: { email, password } });
    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/orders$/);
    await use(page);
  },
});

export { expect };

/** A valid one-page PDF, so the same upload spec also passes pypdf on the real API. */
export function minimalPdf(name = "DME Patient Demo Document CPAP.fax.pdf") {
  const objs = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>",
  ];
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((body, i) => {
    offsets.push(out.length);
    out += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = out.length;
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const o of offsets) out += `${String(o).padStart(10, "0")} 00000 n \n`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return { name, mimeType: "application/pdf", buffer: Buffer.from(out) };
}

/** App alerts only: Next's route announcer is also role="alert". */
export const alertOf = (page: Page) => page.locator('[role="alert"]:not(#__next-route-announcer__)');
