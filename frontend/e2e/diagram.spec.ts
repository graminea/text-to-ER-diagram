import { expect, test } from "@playwright/test";
import type { ERSchema } from "../src/types";
const names = ["Livro", "Editora", "Autor", "Exemplar", "Usuario", "Emprestimo", "Reserva"];
const schema: ERSchema = {
  entities: names.map(name => ({ name, attributes: [
    { name: "id", data_type: "integer", is_identifier: true },
    { name: "descricao", data_type: "string", is_identifier: false },
    { name: "data_cadastro", data_type: "date", is_identifier: false },
  ] })),
  relationships: [[0, 1, "Publicacao"], [0, 2, "Autoria"], [0, 3, "Exemplares_de_livro"], [3, 5, "Item_emprestado"], [4, 5, "Registro_emprestimo"], [4, 6, "Registro_reserva"], [3, 6, "Exemplar_reservado"], [0, 2, "Revisao"], [4, 4, "Indicacao"]].map(([a, b, name]) => ({
    name: String(name), participants: [
      { entity: names[Number(a)], role: "origem", min_cardinality: 0, max_cardinality: "N" },
      { entity: names[Number(b)], role: "destino", min_cardinality: 1, max_cardinality: 1 },
    ],
  })), assumptions: [], ambiguities: [],
};
for (const width of [1440, 390]) {
  test(`complex diagram fits its routed connections at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.route("**/api/generations", async route => {
      if (route.request().method() !== "POST") return route.continue();
      const response = await route.fetch();
      const payload = await response.json();
      await route.fulfill({ response, json: { ...payload, schema_model: schema } });
    });
    await page.goto("/");
    await page.getByRole("button", { name: "Gerar diagrama" }).click();
    await expect(page.locator(".react-flow__node-relationship")).toHaveCount(9);
    await expect(page.locator(".react-flow__edge")).toHaveCount(18);
    await page.evaluate(() => document.fonts.ready);
    const fits = () => page.evaluate(() => {
      const viewport = document.querySelector(".react-flow")!.getBoundingClientRect();
      return [...document.querySelectorAll(".react-flow__node-default, .react-flow__node-relationship, .react-flow__edge-path, .cardinality-label")].every(element => {
        const box = element.getBoundingClientRect();
        return box.left >= viewport.left - 1 && box.right <= viewport.right + 1 && box.top >= viewport.top - 1 && box.bottom <= viewport.bottom + 1;
      });
    });
    await expect.poll(fits).toBe(true);
    await page.screenshot({ path: `test-results/complex-diagram-${width}.png`, fullPage: true });
    await page.locator(".react-flow__controls-fitview").click();
    await expect.poll(fits).toBe(true);
  });
}
