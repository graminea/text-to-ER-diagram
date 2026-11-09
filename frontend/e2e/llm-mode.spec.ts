import { expect, test } from "@playwright/test";

test("live configuration replaces mock labels and shows safe provider errors", async ({ page }) => {
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
  await expect(page.locator(".mode")).toHaveText("LLM direta");
  await expect(page.locator("#mock-note")).toContainText("gemini/test-model");
  await expect(page.locator("#mock-note")).not.toContainText("Cliente/Pedido");
  await page.getByRole("button", { name: "Gerar diagrama" }).click();
  await expect(page.getByRole("alert")).toContainText("chave");
  await expect(page.getByRole("alert")).not.toContainText("untrusted-provider-detail");
  await expect(page.getByRole("button", { name: "Gerar diagrama" })).toBeEnabled();
  await expect(page.getByLabel("Requisitos do sistema")).toHaveValue(/Um cliente/);
  await page.screenshot({ path: "test-results/llm-mode-error.png", fullPage: true });
});

test("live mode presents model and usage alongside the validated diagram", async ({ page }) => {
  await page.route("**/api/health", (route) => route.fulfill({
    json: { status: "ok", provider: "litellm", mode: "llm", model: "openai/test-model" },
  }));
  await page.route("**/api/generations", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const response = await route.fetch();
    const payload = await response.json();
    await route.fulfill({ response, json: {
      ...payload, provider: "litellm", model: "openai/test-model",
      input_tokens: 120, output_tokens: 80, call_count: 1,
    } });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Gerar diagrama" }).click();
  await expect(page.getByText("Estrutura válida")).toBeVisible();
  await expect(page.locator(".entity-title")).toHaveCount(2);
  await page.getByText("Decisões e validação").click();
  await expect(page.locator(".provider-info")).toContainText("openai/test-model");
  await expect(page.locator(".provider-info")).toContainText("120 tokens de entrada");
  await expect(page.locator(".provider-info")).toContainText("80 tokens de saída");
});
