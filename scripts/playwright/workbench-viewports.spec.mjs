import { expect, test } from "@playwright/test";

const reachableControls = [
  "#workflow-list",
  "#step-list",
  "#inspector-tab-workflow",
  "#inspector-tab-step",
  "#inspector-tab-target",
  "#dry-run-selected",
  "#background-run-selected",
  "#stop-dry-run",
];

test.beforeEach(async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.locator("body[data-workbench-mode]").waitFor({ state: "attached", timeout: 60_000 });
  await page.locator("#workflow-list .workflow-row").first().waitFor({ state: "visible", timeout: 60_000 });
  await page.locator("#step-list .step-row").first().waitFor({ state: "visible", timeout: 60_000 });
});

test("workbench has no horizontal overflow and keeps primary lists reachable", async ({ page }, testInfo) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(String(error)));

  const metrics = await page.evaluate(() => {
    const rect = (selector) => {
      const element = document.querySelector(selector);
      const box = element?.getBoundingClientRect();
      return box
        ? { x: box.x, y: box.y, width: box.width, height: box.height, bottom: box.bottom, right: box.right }
        : null;
    };
    return {
      viewport: { width: innerWidth, height: innerHeight },
      mode: document.body.dataset.workbenchMode,
      density: document.body.dataset.workbenchDensity,
      documentWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      workflowList: rect("#workflow-list"),
      stepList: rect("#step-list"),
      runPanel: rect(".run-panel"),
    };
  });

  expect(metrics.documentWidth, JSON.stringify(metrics)).toBeLessThanOrEqual(metrics.clientWidth + 1);
  expect(metrics.workflowList?.height, JSON.stringify(metrics)).toBeGreaterThanOrEqual(95);
  expect(metrics.stepList?.height, JSON.stringify(metrics)).toBeGreaterThanOrEqual(95);
  expect(pageErrors).toEqual([]);

  for (const selector of reachableControls) {
    const locator = page.locator(selector).first();
    await locator.scrollIntoViewIfNeeded();
    await expect(locator, `${selector} must remain visible after scrolling`).toBeVisible();
  }

  await testInfo.attach("viewport-metrics", {
    body: Buffer.from(JSON.stringify(metrics, null, 2)),
    contentType: "application/json",
  });
  await page.screenshot({ path: testInfo.outputPath(`${testInfo.project.name}-full.png`), fullPage: true });
});

test("inspector tabs support pointer, keyboard, and selection-driven navigation", async ({ page }) => {
  const workflowTab = page.locator("#inspector-tab-workflow");
  const stepTab = page.locator("#inspector-tab-step");
  const targetTab = page.locator("#inspector-tab-target");

  await expect(workflowTab).toHaveAttribute("aria-selected", "true");
  await workflowTab.focus();
  await page.keyboard.press("ArrowRight");
  await expect(stepTab).toBeFocused();
  await expect(stepTab).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("#inspector-panel-step")).toBeVisible();

  await page.keyboard.press("ArrowRight");
  await expect(targetTab).toBeFocused();
  await expect(targetTab).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("#inspector-panel-target")).toBeVisible();

  await page.locator("#workflow-list .workflow-row").first().click();
  await expect(workflowTab).toHaveAttribute("aria-selected", "true");
  await page.locator("#step-list .step-row").first().click();
  await expect(stepTab).toHaveAttribute("aria-selected", "true");
  await page.locator("#inspector-tab-target").click();
  await page.locator("#target-list .target-row").first().click();
  await expect(targetTab).toHaveAttribute("aria-selected", "true");
});
