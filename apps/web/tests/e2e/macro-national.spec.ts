import { test, expect } from "@playwright/test";

const EMAIL = process.env.ADMIN_EMAIL ?? "admin@rsu.local";
const PASSWORD = process.env.ADMIN_PASSWORD ?? "change-me-in-prod";

test("admin logs in, sees hub, navigates to Macro National", async ({ page }) => {
  await page.goto("/dashboard");
  // middleware redirects to /login
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Mot de passe").fill(PASSWORD);
  await page.getByRole("button", { name: "Se connecter" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Tableaux de bord" })).toBeVisible();
  await expect(page.getByText("Macro National")).toBeVisible();

  await page.getByRole("link", { name: "Consulter" }).click();
  await expect(page).toHaveURL(/\/dashboard\/macro-national/);
  await expect(
    page.getByRole("heading", {
      name: "Tableau de bord hebdomadaire de suivi RSU",
    }),
  ).toBeVisible();
  // At least one section header from section 5.1 must render.
  await expect(page.getByText("Chiffres clés des inscriptions")).toBeVisible();
});
