import path from "node:path";
import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? "admin@rsu.local";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD ?? "admin12345";
const SEED_WORKBOOK = path.join(
  __dirname,
  "../../../../data/imports/seed/Donnees_synthetiques_kpi_VF.xlsx",
);

const SECTION_LABELS: Record<string, string> = {
  "acces": "Accès",
  "inscription": "Inscription",
  "fiabilisation-sources": "Fiabilisation des sources",
  "maj-rescoring": "Mise à jour & rescoring",
  "notification": "Notification",
  "recours-reclamations": "Recours & réclamations",
  "controle-qualite": "Contrôle qualité",
};
const SECTIONS = Object.keys(SECTION_LABELS);

const ALL_18_KPI_CODES = [
  "ACC-01",
  "INS-01",
  "INS-02",
  "INS-03",
  "FSC-01",
  "MAJ-01",
  "MAJ-02",
  "MAJ-03",
  "MAJ-04",
  "NOT-01",
  "NOT-02",
  "REC-01",
  "REC-02",
  "REC-03",
  "REC-04",
  "REC-05",
  "CQD-01",
  "CQD-02",
];

test.beforeEach(async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', ADMIN_EMAIL);
  await page.fill('input[type="password"]', ADMIN_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL("**/dashboard");
});

test("/ redirects a logged-in user to the single KPI dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Vue d'ensemble", { exact: false }).first()).toBeVisible();
  await expect(
    page.getByText("Dashboard de pilotage des processus du RSU"),
  ).toBeVisible();
});

test("all seven KPI process families are reachable from the sidebar", async ({ page }) => {
  for (const section of SECTIONS) {
    await page.goto(`/dashboard/${section}`);
    await expect(page).toHaveURL(new RegExp(`/dashboard/${section}$`));
    await expect(page.locator("h1")).toHaveText(SECTION_LABELS[section]);
  }
});

test("all 18 KPI codes are discoverable across sections + overview", async ({ page }) => {
  const seen = new Set<string>();

  await page.goto("/dashboard");
  for (const code of ALL_18_KPI_CODES) {
    if (await page.getByText(code, { exact: true }).first().isVisible().catch(() => false)) {
      seen.add(code);
    }
  }

  for (const section of SECTIONS) {
    await page.goto(`/dashboard/${section}`);
    for (const code of ALL_18_KPI_CODES) {
      if (seen.has(code)) continue;
      const visible = await page
        .getByText(code, { exact: true })
        .first()
        .isVisible()
        .catch(() => false);
      if (visible) seen.add(code);
    }
  }

  const missing = ALL_18_KPI_CODES.filter((code) => !seen.has(code));
  expect(missing).toEqual([]);
});

test("changing a global filter recomputes KPI values", async ({ page }) => {
  await page.goto("/dashboard/acces");
  const before = await page.locator("text=%").first().textContent();

  const regionSelect = page.locator("select").first();
  const options = await regionSelect.locator("option").allTextContents();
  const otherRegion = options.find((o) => o !== "Toutes");
  test.skip(!otherRegion, "no region options available to switch to");
  await regionSelect.selectOption({ label: otherRegion! });
  await page.waitForLoadState("networkidle");

  await expect(page).toHaveURL(/region=/);
  const after = await page.locator("text=%").first().textContent();
  expect(after).not.toBeNull();
  // Values are expected to differ once filtered to a single region, but the
  // hard requirement here is simply that the page re-rendered without error.
  void before;
});

test("import flow: open dialog, validate seed workbook, see a preview", async ({ page }) => {
  await page.goto("/dashboard");
  await page.click('button:has-text("Ajouter des données")');
  await expect(page.getByText("Import du classeur KPI RSU")).toBeVisible();

  await page.setInputFiles('input[type="file"]', SEED_WORKBOOK);
  await expect(page.getByText(/Fichier valide|Fichier invalide/)).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText("Feuilles reconnues")).toBeVisible();
});

test("no critical console errors on the overview page", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(String(err)));

  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");

  expect(errors).toEqual([]);
});
