import { expect, test } from "@playwright/test";

test("Scenario A creates a hire and opens readiness overview", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Demo persona").selectOption("admin-1");
  await page.getByRole("button", { name: "Enter workspace" }).click();
  await expect(page.getByRole("heading", { name: "Command center" })).toBeVisible();

  await page.getByRole("button", { name: "New hire" }).click();
  await page.getByLabel("Full name").fill("Scenario A Hire");
  await page.getByLabel("Email").fill("scenario-a@example.test");
  await page.getByLabel("Job title").fill("Engineer");
  await page.getByLabel("Department").fill("Engineering");
  await page.getByLabel("Join date").fill("2026-12-01");
  await page.getByLabel("Work state").fill("KA");
  await page.getByRole("button", { name: "Generate plan" }).click();

  await expect(page.getByRole("heading", { name: "Scenario A Hire" })).toBeVisible();
  await expect(page.getByText("Readiness score")).toBeVisible();
  await expect(page.getByRole("button", { name: "Plan" })).toBeVisible();
});
