import { expect, test } from "@playwright/test";

for (const viewport of [
  { width: 1440, height: 1000 },
  { width: 390, height: 844 },
]) {
  test(`workspace remains usable at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Nenhum modelo" }),
    ).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: `test-results/workspace-${viewport.width}-empty.png`,
      fullPage: true,
    });
    await page.getByLabel("Requisitos do sistema").fill("curto");
    await expect(
      page.getByRole("button", { name: "Gerar diagrama" }),
    ).toBeDisabled();
    await page
      .getByLabel("Requisitos do sistema")
      .fill(
        "Um cliente pode fazer vários pedidos. Cada pedido pertence a exatamente um cliente.",
      );
    await page.getByRole("button", { name: "Gerar diagrama" }).click();
    await expect(page.getByText("Estrutura válida")).toBeVisible();
    await expect(page.locator(".entity-title")).toHaveCount(2);
    await expect
      .poll(
        async () =>
          (await page.locator(".react-flow__node-default").first().boundingBox())
            ?.width ?? 0,
      )
      .toBeGreaterThan(170);
    await expect(page.locator(".relationship-name")).toHaveText("realiza");
    await expect(page.locator(".cardinality-label text")).toHaveText(["0..N", "1..1"]);
    await page.getByText("Decisões e validação").click();
    await page.getByText("Ver JSON canônico").click();
    await expect(page.locator("pre")).toContainText("Cliente");
    await page.screenshot({
      path: `test-results/workspace-${viewport.width}-result.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.reload();
    await page.locator(".history > summary").click();
    await page.locator(".history-item").first().click();
    await expect(page.locator(".history-item").first()).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(page.locator(".react-flow__node-default")).toHaveCount(2);
  });
}

test("generation failure preserves requirements and allows retry", async ({
  page,
}) => {
  await page.goto("/");
  await page.route("**/api/generations", async (route) => {
    if (route.request().method() === "POST")
      await route.fulfill({ status: 502, body: "{}" });
    else await route.continue();
  });
  await page.getByRole("button", { name: "Gerar diagrama" }).click();
  await expect(page.getByRole("alert")).toContainText("Tente novamente");
  await expect(page.getByLabel("Requisitos do sistema")).toHaveValue(
    /Um cliente/,
  );
  await expect(
    page.getByRole("button", { name: "Gerar diagrama" }),
  ).toBeEnabled();
  await page.unroute("**/api/generations");
  await page.getByRole("button", { name: "Gerar diagrama" }).click();
  await expect(page.getByText("Estrutura válida")).toBeVisible();
});
