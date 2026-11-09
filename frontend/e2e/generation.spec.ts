import { expect, test } from "@playwright/test";

test("generate, inspect and reload a persisted ER diagram", async ({
  page,
}) => {
  await page.goto("/");
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/generations") && r.request().method() === "POST",
    ),
    page.getByRole("button", { name: "Gerar diagrama" }).click(),
  ]);
  expect(response.status()).toBe(201);
  await expect(page.getByText("Estrutura válida")).toBeVisible();
  await expect(page.locator(".react-flow__node-default")).toHaveCount(2);
  await expect(page.locator(".react-flow__edge")).toHaveCount(2);
  await page.screenshot({ path: "test-results/demo.png", fullPage: true });
  await page.getByText("Decisões e validação").click();
  await page.getByText("Ver JSON canônico").click();
  await expect(page.locator("pre")).toContainText("Cliente");
  await page.reload();
  await page.locator(".history > summary").click();
  await page.locator(".history-item").first().click();
  await expect(page.getByText("Estrutura válida")).toBeVisible();
  await expect(page.locator(".react-flow__node-default")).toHaveCount(2);
});
