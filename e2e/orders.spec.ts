import { benchmarkOrder, expect, manualOrder, REAL_API, test } from "./fixtures";

test("manual create, edit and delete @AC-M4.4", async ({ signedIn: page }) => {
  await page.goto("/orders/new?tab=manual");
  await page.getByRole("main").getByLabel("Patient first name").fill("Jane");
  await page.getByRole("main").getByLabel("Patient last name").fill("Doe");
  await page.getByRole("main").getByLabel("Date of birth").fill("1961-03-14");
  await page.getByRole("main").getByLabel("Ordering provider name").fill("Ann Lee MD");
  await page.getByRole("main").getByLabel("Ordering provider NPI").fill("1234567893");
  await page.getByRole("button", { name: "Create order" }).click();

  await expect(page).toHaveURL(/\/orders\/[0-9a-f]{8}-[0-9a-f-]{27}$/);
  await expect(page.getByRole("main").getByTestId("status-badge")).toHaveText("Ready");

  await page.getByRole("link", { name: "← Orders" }).click();
  await expect(page.getByRole("row", { name: /Doe, Jane/ })).toBeVisible();

  await page.getByRole("link", { name: "Doe, Jane" }).click();
  await page.getByRole("main").getByLabel("Ordering provider name").fill("Ann Lee MD PhD");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Changes saved")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("main").getByLabel("Ordering provider name")).toHaveValue("Ann Lee MD PhD");

  await page.getByRole("button", { name: "Delete order" }).click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog).toContainText("Delete this order?");
  await dialog.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page).toHaveURL(/\/orders$/);
  await expect(page.getByRole("row", { name: /Doe, Jane/ })).toHaveCount(0);
});

test("an incomplete manual order is flagged, not guessed @AC-M4.4", async ({ signedIn: page }) => {
  await page.goto("/orders/new?tab=manual");
  await page.getByRole("main").getByLabel("Patient first name").fill("Daniel");
  await page.getByRole("main").getByLabel("Patient last name").fill("Okafor");
  await page.getByRole("button", { name: "Create order" }).click();
  await expect(page.getByRole("main").getByTestId("status-badge")).toHaveText("Needs review");
  await expect(page.getByRole("main").getByLabel("Date of birth")).toHaveAttribute("aria-invalid", "true");
});

test("cancelling the delete dialog keeps the order @AC-M4.4", async ({ signedIn: page, stub }) => {
  stub.seed(manualOrder("33333333-3333-4333-8333-333333333333", { patient_first_name: "Jane", patient_last_name: "Doe" }));
  await page.goto("/orders/33333333-3333-4333-8333-333333333333");
  await page.getByRole("button", { name: "Delete order" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Doe, Jane" })).toBeVisible();
});

test("status tabs filter the list via ?status= @AC-M4.4", async ({ signedIn: page, stub }) => {
  test.skip(REAL_API, "seeds the stub");
  stub.seed(
    benchmarkOrder(),
    manualOrder("44444444-4444-4444-8444-444444444444", {
      patient_first_name: "Jane", patient_last_name: "Doe", patient_dob: "1961-03-14", provider_name: "Ann Lee MD", provider_npi: "1234567893",
    }),
  );
  await page.goto("/orders");
  await expect(page.getByRole("row")).toHaveCount(3);

  await page.getByRole("link", { name: "Ready" }).click();
  await expect(page).toHaveURL(/status=ready/);
  await expect(page.getByRole("row", { name: /Doe, Jane/ })).toBeVisible();
  await expect(page.getByRole("row", { name: /Curie, Marie/ })).toHaveCount(0);

  await page.getByRole("link", { name: "Needs review" }).click();
  await expect(page.getByRole("row", { name: /Curie, Marie/ })).toBeVisible();
  await expect(page.getByRole("row", { name: /Doe, Jane/ })).toHaveCount(0);
});

test("the list shows a skeleton while loading @AC-M4.5", async ({ signedIn: page, stub }) => {
  test.skip(REAL_API, "needs a slow API");
  stub.delayMs = 800;
  await page.reload();
  await expect(page.getByRole("main").getByLabel("Loading orders")).toBeVisible();
  await expect(page.getByRole("heading", { name: "No orders yet" })).toBeVisible();
});

test("a failing list shows an error banner with retry @AC-M4.5", async ({ signedIn: page, stub }) => {
  test.skip(REAL_API, "needs a failing API");
  stub.listStatus = 500;
  await page.reload();
  await expect(page.getByText("Couldn't load orders")).toBeVisible();
  stub.listStatus = 0;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("heading", { name: "No orders yet" })).toBeVisible();
});

test("a 401 clears the session and returns to login @AC-M4.1", async ({ signedIn: page, stub }) => {
  test.skip(REAL_API, "needs a forced 401");
  await page.evaluate(() => sessionStorage.setItem("dme-intake-token", "expired"));
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
  void stub;
});

test("orders list and review fit 390px @AC-M4.4", async ({ signedIn: page, stub }) => {
  test.skip(REAL_API, "seeds the stub");
  stub.seed(benchmarkOrder());
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/orders");
  await expect(page.getByRole("row", { name: /Curie, Marie/ })).toBeVisible();
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(await overflow()).toBeLessThanOrEqual(0);
  await page.goto("/orders/11111111-1111-4111-8111-111111111111");
  await expect(page.getByRole("main").getByLabel("Ordering provider NPI")).toBeVisible();
  expect(await overflow()).toBeLessThanOrEqual(0);
});
