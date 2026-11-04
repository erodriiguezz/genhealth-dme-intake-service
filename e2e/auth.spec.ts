import { alertOf, expect, test } from "./fixtures";

const uniqueEmail = () => `qa-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;

test("sign up lands on the empty orders list, logout returns to login @AC-M4.1", async ({ page, stub }) => {
  void stub;
  await page.goto("/signup");
  await page.getByLabel("Email").fill(uniqueEmail());
  await page.getByLabel("Password").fill("correct-horse-9");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/orders$/);
  await expect(page.getByRole("heading", { name: "No orders yet" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("bad credentials show an inline error @AC-M4.1", async ({ page, stub }) => {
  void stub;
  await page.goto("/login");
  await page.getByLabel("Email").fill("nobody@example.com");
  await page.getByLabel("Password").fill("wrong-password-1");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(alertOf(page)).toContainText("Email or password is incorrect.");
  await expect(page).toHaveURL(/\/login$/);
});

test("visiting /orders signed out redirects to /login @AC-M4.1", async ({ page, stub }) => {
  void stub;
  await page.goto("/orders");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("every page carries the demo banner and the footer @AC-M4.1", async ({ page, stub }) => {
  void stub;
  await page.goto("/login");
  await expect(page.getByText("Demo environment. Do not upload real patient data.")).toBeVisible();
  await expect(page.getByText("Take-home project for GenHealth.ai by Ernesto Rodriguez.")).toBeVisible();
});
