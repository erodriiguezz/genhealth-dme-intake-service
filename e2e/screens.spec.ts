import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { benchmarkOrder, expect, manualOrder, test } from "./fixtures";

// Evidence capture for AC-M4.6. Run with SCREENSHOTS=1; it needs the stubbed API.
test.skip(process.env.SCREENSHOTS !== "1", "set SCREENSHOTS=1 to capture evidence screenshots");
test.use({ bypassCSP: true }); // axe is injected as an inline script

const OUT = process.env.EVIDENCE_DIR ?? "../docs/evidence/M4";
const AXE = join(homedir(), ".claude/skills/design/node_modules/axe-core/axe.min.js");
const findings: { screen: string; width: number; id: string; impact: string; target: string }[] = [];

const WIDTHS = [1280, 390];

test.afterAll(() => {
  mkdirSync(OUT, { recursive: true });
  writeFileSync(join(OUT, "axe.json"), JSON.stringify(findings, null, 2));
});

async function shoot(page: import("@playwright/test").Page, name: string, ready: () => Promise<void>) {
  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: width > 600 ? 900 : 844 });
    await ready();
    await page.screenshot({ path: join(OUT, `${name}-${width}.png`), fullPage: true });
    await page.addScriptTag({ content: readFileSync(AXE, "utf8") });
    const results = await page.evaluate(async () => {
      // @ts-expect-error injected axe global
      const r = await axe.run(document, { resultTypes: ["violations"] });
      return r.violations.map((v: { id: string; impact: string; nodes: { target: string[] }[] }) => ({ id: v.id, impact: v.impact, target: v.nodes[0]?.target.join(" ") }));
    });
    for (const v of results) findings.push({ screen: name, width, ...v });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `${name}@${width} horizontal overflow`).toBeLessThanOrEqual(0);
  }
}

test("capture screens and run axe @AC-M4.6", async ({ page, stub, signedIn }) => {
  void signedIn;
  const reload = async () => {
    await page.reload();
  };

  await shoot(page, "orders-empty", async () => {
    await reload();
    await expect(page.getByRole("heading", { name: "No orders yet" })).toBeVisible();
  });

  stub.seed(
    benchmarkOrder(),
    manualOrder("44444444-4444-4444-8444-444444444444", {
      patient_first_name: "Jane", patient_last_name: "Doe", patient_dob: "1961-03-14", provider_name: "Ann Lee MD", provider_npi: "1234567893",
    }),
    manualOrder("55555555-5555-4555-8555-555555555555", {
      patient_first_name: "Daniel", patient_last_name: "Okafor", provider_name: "Priya Natarajan MD", provider_npi: "1093817465",
    }),
  );
  await shoot(page, "orders-filled", async () => {
    await reload();
    await expect(page.getByRole("row", { name: /Curie, Marie/ })).toBeVisible();
  });

  await page.goto("/orders/new");
  await shoot(page, "orders-new-upload", async () => {
    await reload();
    await expect(page.getByRole("button", { name: "Choose PDF" })).toBeVisible();
  });
  await page.goto("/orders/new?tab=manual");
  await shoot(page, "orders-new-manual", async () => {
    await reload();
    await expect(page.getByRole("button", { name: "Create order" })).toBeVisible();
  });

  await page.goto("/orders/11111111-1111-4111-8111-111111111111");
  await shoot(page, "order-needs-review", async () => {
    await reload();
    await expect(page.getByRole("main").getByTestId("status-badge")).toHaveText("Needs review");
  });

  await page.getByRole("main").getByLabel("Ordering provider NPI").fill("1234567893");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("main").getByTestId("status-badge")).toHaveText("Ready");
  await shoot(page, "order-ready", async () => {
    await page.waitForTimeout(700); // let the toast and the field transitions settle
    await expect(page.getByRole("main").getByTestId("status-badge")).toHaveText("Ready");
  });

  await page.goto("/orders/00000000-0000-4000-8000-000000000000");
  await shoot(page, "order-not-found", async () => {
    await expect(page.getByRole("heading", { name: "Order not found" })).toBeVisible();
  });

  const serious = findings.filter((f) => f.impact === "critical" || f.impact === "serious");
  expect(serious).toEqual([]);
});
