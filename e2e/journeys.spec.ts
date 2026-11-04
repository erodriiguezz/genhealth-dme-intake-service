import { mkdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { API_URL } from "./fixtures";

// Deployed journeys. Run against live: E2E_REAL_API=1 BASE_URL=<web> API_URL=<api> pnpm exec playwright test journeys.spec.ts
test.skip(process.env.E2E_REAL_API !== "1", "journeys need the real API (E2E_REAL_API=1)");
test.describe.configure({ mode: "serial" });
test.setTimeout(150_000);

const CASES = resolve(__dirname, "../evals/cases");
const OUT = resolve(__dirname, "../docs/evidence/M6");
const PASSWORD = "correct-horse-9";
const email = (tag: string) => `qa-${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
const shot = (page: Page, name: string) => page.screenshot({ path: join(OUT, `${name}.png`), fullPage: true });

mkdirSync(OUT, { recursive: true });

async function signUp(page: Page, tag: string) {
  await page.goto("/signup");
  await page.getByLabel("Email").fill(email(tag));
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/orders$/);
}

async function tokenOf(page: Page) {
  return page.evaluate(() => sessionStorage.getItem("dme-intake-token"));
}

async function deleteAllOrders(request: APIRequestContext, token: string | null) {
  if (!token) return;
  const headers = { Authorization: `Bearer ${token}` };
  const list = await request.get(`${API_URL}/orders`, { headers });
  if (!list.ok()) return;
  for (const o of (await list.json()).items) await request.delete(`${API_URL}/orders/${o.id}`, { headers });
}

async function apiUser(request: APIRequestContext, tag: string) {
  const addr = email(tag);
  const reg = await request.post(`${API_URL}/auth/register`, { data: { email: addr, password: PASSWORD } });
  expect(reg.status()).toBe(201);
  const login = await request.post(`${API_URL}/auth/login`, { form: { username: addr, password: PASSWORD } });
  expect(login.status()).toBe(200);
  return { Authorization: `Bearer ${(await login.json()).access_token}` };
}

const main = (page: Page) => page.getByRole("main");

test("AC-M6.1 sign up, upload the benchmark fax, fix the NPI, order is ready @AC-M6.1", async ({ page, request }) => {
  await signUp(page, "j1");
  try {
    await page.goto("/orders/new");
    await page.locator('input[type="file"]').setInputFiles(join(CASES, "genhealth-cpap-fax.pdf"));
    await expect(page.getByText(/Reading document… \d+s/)).toBeVisible();
    await expect(page).toHaveURL(/\/orders\/[0-9a-f]{8}-[0-9a-f-]{27}$/, { timeout: 90_000 });

    const m = main(page);
    await expect(m.getByLabel("Patient first name")).toHaveValue("Marie");
    await expect(m.getByLabel("Patient last name")).toHaveValue("Curie");
    await expect(m.getByLabel("Date of birth")).toHaveValue("1900-12-05");
    await expect(m.getByLabel("Ordering provider name")).toHaveValue(/Arjun Raj/);
    await expect(m.getByLabel("Ordering provider NPI")).toHaveValue("9182734556");

    await expect(m.getByLabel("Ordering provider NPI")).toHaveAttribute("aria-invalid", "true");
    await expect(m.getByText("An NPI starts with 1 or 2.")).toBeVisible();
    await expect(m.getByText(/Fails the NPI checksum/)).toBeVisible();
    await expect(m.getByTestId("status-badge")).toHaveText("Needs review");
    await expect(m.getByText(/Also on the document:/)).toContainText("Gregory House");
    await shot(page, "journey-1-needs-review");

    await m.getByLabel("Ordering provider NPI").fill("1234567893");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(m.getByTestId("status-badge")).toHaveText("Ready");
    await expect(m.getByText("All fields verified")).toBeVisible();
    await expect(m.getByText(/Fails the NPI checksum/)).toHaveCount(0);
    await page.waitForTimeout(600);
    await shot(page, "journey-1-ready");
  } finally {
    await deleteAllOrders(request, await tokenOf(page));
  }
});

test("AC-M6.2 another user cannot see, open or download my order @AC-M6.2", async ({ page, request }) => {
  const a = await apiUser(request, "a");
  const upload = await request.post(`${API_URL}/orders/extract`, {
    headers: a,
    multipart: { file: { name: "genhealth-cpap-fax.pdf", mimeType: "application/pdf", buffer: readFileSync(join(CASES, "genhealth-cpap-fax.pdf")) } },
    timeout: 120_000,
  });
  expect(upload.status()).toBe(201);
  const orderId = (await upload.json()).id as string;

  try {
    expect((await request.get(`${API_URL}/orders/${orderId}/document`, { headers: a })).status()).toBe(200);

    await signUp(page, "b");
    await expect(page.getByRole("heading", { name: "No orders yet" })).toBeVisible();
    await expect(page.getByText("Curie, Marie")).toHaveCount(0);

    await page.goto(`/orders/${orderId}`);
    await expect(page.getByRole("heading", { name: "Order not found" })).toBeVisible();
    await shot(page, "journey-2-not-found");

    const b = { Authorization: `Bearer ${await tokenOf(page)}` };
    expect((await request.get(`${API_URL}/orders/${orderId}`, { headers: b })).status()).toBe(404);
    expect((await request.get(`${API_URL}/orders/${orderId}/document`, { headers: b })).status()).toBe(404);
    expect((await request.delete(`${API_URL}/orders/${orderId}`, { headers: b })).status()).toBe(404);
    expect((await request.get(`${API_URL}/orders/${orderId}`, { headers: a })).status()).toBe(200);
  } finally {
    await request.delete(`${API_URL}/orders/${orderId}`, { headers: a });
  }
});

test("AC-M6.3 a fax without a date of birth is flagged, never guessed @AC-M6.3", async ({ page, request }) => {
  await signUp(page, "j3");
  try {
    await page.goto("/orders/new");
    await page.locator('input[type="file"]').setInputFiles(join(CASES, "missing-dob.pdf"));
    await expect(page).toHaveURL(/\/orders\/[0-9a-f]{8}-[0-9a-f-]{27}$/, { timeout: 90_000 });

    const m = main(page);
    const dob = m.getByLabel("Date of birth");
    await expect(dob).toHaveValue("");
    await expect(dob).toHaveAttribute("aria-invalid", "true");
    await expect(m.getByText("Not found. Enter it manually.")).toBeVisible();
    await expect(m.getByTestId("status-badge")).toHaveText("Needs review");
    await shot(page, "journey-3-missing-dob");
  } finally {
    await deleteAllOrders(request, await tokenOf(page));
  }
});
