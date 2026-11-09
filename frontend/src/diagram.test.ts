import { describe, expect, it } from "vitest";
import { toDiagram, type DiagramPort } from "./diagram";
import type { ERSchema } from "./types";
const schema: ERSchema = {
  entities: ["Cliente", "Pedido"].map(name => ({ name, attributes: [
    { name: "id", data_type: "integer", is_identifier: true },
  ] })),
  relationships: [{ name: "realiza", participants: [
    { entity: "Cliente", role: "comprador", min_cardinality: 0, max_cardinality: "N" },
    { entity: "Pedido", role: "compra", min_cardinality: 1, max_cardinality: 1 },
  ] }], assumptions: [], ambiguities: [],
};
export const complexSchema: ERSchema = {
  ...schema,
  entities: ["Livro", "Editora", "Autor", "Exemplar", "Usuario", "Emprestimo", "Reserva"].map(name => ({
    name, attributes: [{ name: "identificador_muito_longo_do_registro", data_type: "integer", is_identifier: true },
      ...Array.from({ length: 7 }, (_, i) => ({ name: `campo_${i}`, data_type: "string" as const, is_identifier: false }))],
  })),
  relationships: [[0, 1], [0, 2], [0, 3], [3, 5], [4, 5], [4, 6], [3, 6], [0, 2], [4, 4]].map(([a, b], i) => ({
    name: `Relacionamento_${i}`, participants: [
      { entity: ["Livro", "Editora", "Autor", "Exemplar", "Usuario", "Emprestimo", "Reserva"][a], role: "origem", min_cardinality: 0, max_cardinality: "N" },
      { entity: ["Livro", "Editora", "Autor", "Exemplar", "Usuario", "Emprestimo", "Reserva"][b], role: "destino", min_cardinality: 1, max_cardinality: 1 },
    ],
  })),
};
describe("ER diagram projection", () => {
  it("preserves identifiers, diamonds and endpoint cardinalities", async () => {
    const graph = await toDiagram(schema);
    expect(graph.nodes.filter(node => node.type === "default")).toHaveLength(2);
    expect(graph.nodes[0].data.fields).toMatchObject([{ is_identifier: true }]);
    expect(graph.nodes.find(node => node.type === "relationship")?.data.label).toBe("realiza");
    expect(graph.edges).toHaveLength(2);
    expect(graph.edges.map(edge => edge.data?.label)).toMatchObject([{ text: "0..N" }, { text: "1..1" }]);
  });
  it("does not draw dangling references in invalid results", async () => {
    const invalid = structuredClone(schema);
    invalid.relationships[0].participants[1].entity = "Ghost";
    const graph = await toDiagram(invalid);
    expect(graph.edges).toEqual([]);
    expect(graph.nodes.some(node => node.type === "relationship")).toBe(false);
  });
  for (const vertical of [false, true]) {
    it(`routes dense, repeated and recursive relationships around entities (${vertical})`, async () => {
      const graph = await toDiagram(complexSchema, vertical);
      const bounds = graph.nodes.find(node => node.type === "bounds")!;
      expect(graph.nodes.filter(node => node.type === "relationship")).toHaveLength(9);
      expect(graph.edges).toHaveLength(18);
      for (const edge of graph.edges) {
        const points = edge.data!.points as { x: number; y: number }[];
        for (const point of points) {
          expect(point.x).toBeGreaterThanOrEqual(0);
          expect(point.y).toBeGreaterThanOrEqual(0);
          expect(point.x).toBeLessThanOrEqual(bounds.width!);
          expect(point.y).toBeLessThanOrEqual(bounds.height!);
        }
        for (let i = 1; i < points.length; i++) {
          const a = points[i - 1], b = points[i];
          expect(Math.min(Math.abs(a.x - b.x), Math.abs(a.y - b.y))).toBeLessThan(0.01);
          for (const node of graph.nodes.filter(node => node.type !== "bounds")) {
            const { x, y } = node.position, right = x + node.width!, bottom = y + node.height!;
            const crosses = Math.abs(a.x - b.x) < 0.01
              ? a.x > x + 0.1 && a.x < right - 0.1 && Math.max(a.y, b.y) > y + 0.1 && Math.min(a.y, b.y) < bottom - 0.1
              : a.y > y + 0.1 && a.y < bottom - 0.1 && Math.max(a.x, b.x) > x + 0.1 && Math.min(a.x, b.x) < right - 0.1;
            expect(crosses, `${edge.id} crosses ${node.id}`).toBe(false);
          }
        }
      }
      const recursive = graph.nodes.find(node => node.id === "entity-4")!;
      const ports = recursive.data.ports as DiagramPort[];
      expect(new Set(ports.map(port => `${port.x},${port.y}`)).size).toBe(ports.length);
      expect(graph.edges.slice(-2).map(edge => edge.data!.label)).toMatchObject([{ text: "0..N (origem)" }, { text: "1..1 (destino)" }]);
    });
  }
});
