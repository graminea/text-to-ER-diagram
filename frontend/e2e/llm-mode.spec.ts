import { expect, test } from "@playwright/test";

test("shows the configured model and safe provider errors", async ({ page }) => {
  await page.route("**/api/health", (route) => route.fulfill({
    json: { status: "ok", provider: "litellm", mode: "llm", model: "gemini/test-model" },
  }));
  await page.route("**/api/generations", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 502, json: { detail: {
        code: "authentication", message: "untrusted-provider-detail",
      } } });
    } else await route.continue();
  });
  await page.goto("/");
  await expect(page.locator(".model-note")).toHaveText("Modelo: gemini/test-model");
  await page.getByRole("button", { name: "Gerar diagrama" }).click();
  await expect(page.getByRole("alert")).toContainText("chave");
  await expect(page.getByRole("alert")).not.toContainText("untrusted-provider-detail");
  await expect(page.getByRole("button", { name: "Gerar diagrama" })).toBeEnabled();
  await expect(page.getByLabel("Requisitos do sistema")).toHaveValue(/Um cliente/);
  await page.screenshot({ path: "test-results/llm-mode-error.png", fullPage: true });
});

test("presents model and usage alongside the validated diagram", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("combobox", { name: "Modo de geração" })).toHaveValue("A");
  await page.getByRole("button", { name: "Gerar diagrama" }).click();
  await expect(page.getByText("Estrutura válida")).toBeVisible();
  await expect(page.locator(".entity-title")).toHaveCount(2);
  await page.getByText("Decisões e validação").click();
  await expect(page.locator(".provider-info")).toContainText("openai/test");
  await expect(page.locator(".provider-info")).toContainText("120 tokens de entrada");
  await expect(page.locator(".provider-info")).toContainText("80 tokens de saída");
});

test("selects agent review and shows combined token usage", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("combobox", { name: "Modo de geração" }).selectOption("B");
  await expect(page.getByText("Com agentes, a geração tende a usar mais tokens.")).toBeVisible();
  const [response] = await Promise.all([
    page.waitForResponse((r) =>
      r.url().endsWith("/api/generations") && r.request().method() === "POST",
    ),
    page.getByRole("button", { name: "Gerar diagrama" }).click(),
  ]);
  expect(response.status()).toBe(201);
  expect(await response.json()).toMatchObject({ flow: "B", call_count: 4 });
  await expect(page.getByText("Estrutura válida")).toBeVisible();
  await expect(page.locator(".entity-title")).toHaveCount(2);
  await page.screenshot({ path: "test-results/agent-generation.png", fullPage: true });
  await page.getByText("Decisões e validação").click();
  await expect(page.locator(".provider-info")).toContainText("Com agentes");
  await expect(page.locator(".provider-info")).toContainText("480 tokens de entrada");
  await expect(page.locator(".provider-info")).toContainText("320 tokens de saída");
});
