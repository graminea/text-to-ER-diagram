import { expect, test } from "@playwright/test";

test("color explorer applies presets, custom colors, surfaces and reset", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".app")).toHaveCSS(
    "background-color",
    "rgb(10, 10, 10)",
  );
  await expect(page.getByRole("button", { name: "Gerar diagrama" })).toHaveCSS(
    "background-color",
    "rgb(245, 245, 245)",
  );
  await page.getByRole("button", { name: "Gerar diagrama" }).click();
  await expect(page.locator(".react-flow__node-default")).toHaveCount(2);
  await page.getByRole("button", { name: "Cores", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Aparência" });
  const swatches = dialog.locator(".swatch");
  await expect(swatches).toHaveCount(20);
  for (const swatch of await swatches.all()) {
    await swatch.click();
    await expect(swatch).toHaveAttribute("aria-pressed", "true");
  }
  await dialog.getByLabel("Cor de destaque: hexadecimal").fill("#25b4aa");
  await dialog.getByLabel("Aplicar destaque também ao diagrama").check();
  await dialog.getByRole("button", { name: "Papel", exact: true }).click();
  await expect(page.locator(".app")).toHaveCSS(
    "background-color",
    "rgb(243, 243, 240)",
  );
  await expect(page.locator(".react-flow")).toHaveClass(/light/);
  await expect(page.locator(".react-flow")).toHaveCSS(
    "--xy-edge-stroke",
    "#25b4aa",
  );
  await dialog.getByLabel("Cor de fundo: hexadecimal").fill("#111820");
  await dialog.getByRole("button", { name: "Concluir" }).click();
  await expect(dialog).not.toBeVisible();
  await page.reload();
  await expect(page.locator(".app")).toHaveCSS(
    "background-color",
    "rgb(17, 24, 32)",
  );
  await expect(page.getByRole("button", { name: "Gerar diagrama" })).toHaveCSS(
    "background-color",
    "rgb(37, 180, 170)",
  );
  await page.getByRole("button", { name: "Cores", exact: true }).click();
  await dialog
    .getByRole("button", { name: "Restaurar preto e branco" })
    .click();
  await expect(page.locator(".app")).toHaveCSS(
    "background-color",
    "rgb(10, 10, 10)",
  );
  await expect(page.getByRole("button", { name: "Gerar diagrama" })).toHaveCSS(
    "background-color",
    "rgb(245, 245, 245)",
  );
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Cores", exact: true }),
  ).toBeFocused();
});

test("color explorer remains usable on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Cores", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(
    await page
      .getByRole("dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/appearance-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Restaurar preto e branco" }).click();
  await page.getByRole("button", { name: "Concluir" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
});
