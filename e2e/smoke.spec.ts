import { expect, test } from "@playwright/test";

const CORS = { "access-control-allow-origin": "*" };

test("home shows the demo banner and API: ok, no console errors @AC-M1.3 @AC-M1.4 @AC-M1.6", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/");
  await expect(page.getByText("Demo only — do not upload real patient data")).toBeVisible();
  await expect(page.getByRole("status")).toHaveText("API: ok");
  expect(errors).toEqual([]);
});

test("shows loading before the API answers @AC-M1.3 @AC-M1.6", async ({ page }) => {
  await page.route("**/health", async (route) => {
    await new Promise((r) => setTimeout(r, 500));
    await route.fulfill({ status: 200, headers: CORS, json: { status: "ok", db: "ok" } });
  });
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText("checking");
  await expect(page.getByRole("status")).toHaveText("API: ok");
});

test("shows degraded when /health is 503 @AC-M1.3 @AC-M1.6", async ({ page }) => {
  await page.route("**/health", (route) =>
    route.fulfill({ status: 503, headers: CORS, json: { status: "degraded", db: "down" } }),
  );
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("API: degraded (db down)");
});

test("shows unreachable when the network fails @AC-M1.3 @AC-M1.6", async ({ page }) => {
  await page.route("**/health", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("API: unreachable");
});

test("home does not overflow at 390px @AC-M1.6", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("API: ok");
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
