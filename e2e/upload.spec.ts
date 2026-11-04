import { alertOf, benchmarkOrder, expect, minimalPdf, REAL_API, test } from "./fixtures";

test("upload shows progress, then the review with all 5 fields and evidence @AC-M4.2", async ({ signedIn: page, stub }) => {
  void stub;
  await page.goto("/orders/new");
  await page.locator('input[type="file"]').setInputFiles(minimalPdf("slow.fax.pdf"));

  await expect(page.getByText(/Reading document… \d+s/)).toBeVisible();
  await expect(page.getByText("slow.fax.pdf")).toBeVisible();
  await expect(page.getByText(/Reading document… [1-9]\d*s/)).toBeVisible({ timeout: 10_000 });

  await expect(page).toHaveURL(/\/orders\/[0-9a-f]{8}-[0-9a-f-]{27}$/, { timeout: 20_000 });
  for (const label of ["Patient first name", "Patient last name", "Date of birth", "Ordering provider name", "Ordering provider NPI"]) {
    await expect(page.getByRole("main").getByLabel(label)).toBeVisible();
  }
  await expect(page.getByRole("main").getByLabel("Patient first name")).toHaveValue("Marie");
  await expect(page.getByRole("main").getByLabel("Date of birth")).toHaveValue("1900-12-05");

  const npi = page.getByRole("main").getByLabel("Ordering provider NPI");
  await expect(npi).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByText(/Fails the NPI checksum/)).toBeVisible();
  const describedBy = await npi.getAttribute("aria-describedby");
  expect(describedBy).toContain("issue-provider_npi-0");

  const evidence = page.getByRole("main").getByTestId("evidence-provider_npi");
  await expect(evidence).toContainText("Prescriber NPI: 9182734556");
  await expect(evidence).toContainText("p.1");
  await expect(page.getByText(/Age|years old/)).toBeVisible();
  const main = page.getByRole("main");
  await expect(main.getByText(/names more than one provider/)).toBeVisible();
  const others = main.getByText(/Also on the document:/);
  await expect(others).toContainText("Gregory House MD, referring physician");
  await expect(others).toContainText("p.2");
  await expect(page.getByRole("main").getByText("An NPI starts with 1 or 2.")).toBeVisible();

  await expect(page.getByRole("main").getByTestId("status-badge")).toHaveText("Needs review");
  await expect(page.getByRole("main").getByText(/errors? must be fixed before this order is ready\./)).toBeVisible();
  await expect(page.getByRole("main").getByText("2 errors must be fixed before this order is ready.")).toBeVisible();
});

test("fixing the NPI and saving makes the order ready, and the list agrees @AC-M4.3", async ({ signedIn: page, stub }) => {
  stub.seed(benchmarkOrder());
  await page.goto("/orders/11111111-1111-4111-8111-111111111111");
  await expect(page.getByRole("main").getByTestId("status-badge")).toHaveText("Needs review");

  await page.getByRole("main").getByLabel("Ordering provider NPI").fill("1234567893");
  await page.getByRole("button", { name: "Save changes" }).click();

  await expect(page.getByRole("main").getByTestId("status-badge")).toHaveText("Ready");
  await expect(page.getByText("All fields verified")).toBeVisible();
  await expect(page.getByText(/Fails the NPI checksum/)).toHaveCount(0);
  await expect(page.getByRole("main").getByLabel("Ordering provider NPI")).not.toHaveAttribute("aria-invalid", "true");

  await page.getByRole("link", { name: "← Orders" }).click();
  const row = page.getByRole("row", { name: /Curie, Marie/ });
  await expect(row).toContainText("Ready");
});

test("a non-PDF is rejected inline before any upload @AC-M4.5", async ({ signedIn: page, stub }) => {
  await page.goto("/orders/new");
  await page.locator('input[type="file"]').setInputFiles({ name: "intake-scan.png", mimeType: "image/png", buffer: Buffer.from("x") });
  await expect(alertOf(page)).toContainText(`"intake-scan.png" isn't a PDF`);
  await expect(page.getByRole("button", { name: "Choose another file" })).toBeVisible();
  expect(stub.extractCalls).toBe(0);
});

test("a file over 20 MB is rejected inline @AC-M4.5", async ({ signedIn: page, stub }) => {
  await page.goto("/orders/new");
  await page.locator('input[type="file"]').setInputFiles({
    name: "huge.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.alloc(20 * 1024 * 1024 + 1, 0x20),
  });
  await expect(alertOf(page)).toContainText("over 20 MB");
  expect(stub.extractCalls).toBe(0);
});

test("a 502 shows an inline error and Try again succeeds @AC-M4.5", async ({ signedIn: page, stub }) => {
  test.skip(REAL_API, "needs a failing extractor");
  await page.goto("/orders/new");
  await page.locator('input[type="file"]').setInputFiles(minimalPdf("referral-502.fax.pdf"));

  await expect(alertOf(page)).toContainText("We couldn't read this document right now. Nothing was saved.");
  await expect(page.getByText("referral-502.fax.pdf")).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page).toHaveURL(/\/orders\/[0-9a-f]{8}-[0-9a-f-]{27}$/);
  expect(stub.extractCalls).toBe(2);
});

test("a 503 shows the extraction-unavailable message with a retry @AC-M4.5", async ({ signedIn: page }) => {
  test.skip(REAL_API, "needs an unconfigured extractor");
  await page.goto("/orders/new");
  await page.locator('input[type="file"]').setInputFiles(minimalPdf("x-503.pdf"));
  await expect(alertOf(page)).toContainText("Extraction isn't available");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
});

test("an unknown order id shows Order not found @AC-M4.5", async ({ signedIn: page }) => {
  await page.goto("/orders/00000000-0000-4000-8000-000000000000");
  await expect(page.getByRole("heading", { name: "Order not found" })).toBeVisible();
  await page.getByRole("link", { name: "Back to orders" }).click();
  await expect(page).toHaveURL(/\/orders$/);
});
