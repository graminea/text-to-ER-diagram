import { Position, type Edge, type Node } from "@xyflow/react";
import type { ELK, ElkNode, ElkExtendedEdge } from "elkjs/lib/elk-api";
import type { ERSchema } from "./types";

export type Diagram = { nodes: Node[]; edges: Edge[] };
export type DiagramPort = { id: string; type: "source" | "target"; side: Position; x: number; y: number };
let engine: Promise<ELK> | undefined;
// Explicit line breaks keep rendered dimensions identical to the routing obstacles.
export function wrapLabel(text: string, columns: number): string {
  return Array.from(text).reduce<string[]>((lines, char, i) => {
    if (i % columns === 0) lines.push("");
    lines[lines.length - 1] += char;
    return lines;
  }, []).join("\n");
}

export async function toDiagram(schema: ERSchema, vertical = false): Promise<Diagram> {
  const nodes: Node[] = schema.entities.map((entity, i) => {
    const title = wrapLabel(entity.name, 28);
    const fields = entity.attributes.map(field => ({ ...field, name: wrapLabel(field.name, 20) }));
    const height = 43 + title.split("\n").length * 18 + fields.reduce((sum, field) => sum + field.name.split("\n").length * 16 + 10, 0);
    return {
      id: `entity-${i}`, type: "default", position: { x: 0, y: 0 },
      width: 250, height, style: { width: 250, height },
      data: { entity, title, fields, ports: [] },
    };
  });
  const ids = new Map(schema.entities.map((entity, i) => [entity.name, `entity-${i}`]));
  const graphNodes: ElkNode[] = nodes.map(node => ({ id: node.id, width: node.width, height: node.height, ports: [] }));
  const edges: ElkExtendedEdge[] = [];
  const connections = new Map<string, { source: string; target: string; sourceHandle: string; targetHandle: string }>();
  schema.relationships.forEach((relationship, i) => {
    const [a, b] = relationship.participants;
    const source = ids.get(a.entity), target = ids.get(b.entity);
    if (!source || !target) return;
    const id = `relationship-${i}`;
    const columns = Math.ceil(relationship.name.length / Math.ceil(relationship.name.length / 18)) || 18;
    const label = wrapLabel(relationship.name, columns);
    const width = Math.max(152, Math.min(columns, relationship.name.length) * 14 + 32);
    const height = Math.max(88, label.split("\n").length * 32 + 32);
    nodes.push({ id, type: "relationship", position: { x: 0, y: 0 }, width, height,
      style: { width, height }, data: { label, ports: [] }, ariaLabel: `Relacionamento: ${relationship.name}` });
    const diamond: ElkNode = { id, width, height, ports: [], layoutOptions: { "elk.portConstraints": "FIXED_POS" } };
    graphNodes.push(diamond);
    [a, b].forEach((participant, endpoint) => {
      const entityId = endpoint === 0 ? source : target;
      const entity = graphNodes.find(node => node.id === entityId)!;
      const entityPort = `${id}-${endpoint}-entity`;
      const diamondPort = `${id}-${endpoint}-diamond`;
      entity.ports!.push({ id: entityPort, width: 0, height: 0 });
      diamond.ports!.push({ id: diamondPort, width: 0, height: 0,
        x: vertical ? width / 2 : endpoint * width,
        y: vertical ? endpoint * height : height / 2,
        layoutOptions: { "elk.port.side": vertical ? (endpoint ? "SOUTH" : "NORTH") : (endpoint ? "EAST" : "WEST") },
      });
      const edgeId = `${id}-${endpoint}`;
      const first = endpoint === 0;
      connections.set(edgeId, { source: first ? entityId : id, target: first ? id : entityId,
        sourceHandle: first ? entityPort : diamondPort, targetHandle: first ? diamondPort : entityPort });
      edges.push({ id: edgeId, sources: [first ? entityPort : diamondPort], targets: [first ? diamondPort : entityPort],
        labels: [{ text: `${participant.min_cardinality}..${participant.max_cardinality}${a.entity === b.entity ? ` (${participant.role})` : ""}`,
          width: (a.entity === b.entity ? participant.role.length + 8 : 4) * 7, height: 18,
          layoutOptions: { "elk.edgeLabels.placement": first ? "HEAD" : "TAIL" } }],
      });
    });
  });
  const elk = await (engine ??= import("elkjs/lib/elk.bundled.js").then(({ default: Layout }) => new Layout()));
  const layout = await elk.layout<ElkNode>({ id: "diagram", children: graphNodes, edges, layoutOptions: {
    "elk.algorithm": "layered", "elk.direction": vertical ? "DOWN" : "RIGHT",
    "elk.edgeRouting": "ORTHOGONAL", "elk.spacing.nodeNode": "64",
    "elk.layered.spacing.nodeNodeBetweenLayers": "90", "elk.spacing.edgeNode": "28",
    "elk.spacing.edgeEdge": "20", "elk.layered.spacing.edgeEdgeBetweenLayers": "24",
    "elk.layered.mergeEdges": "false", "elk.padding": "[top=24,left=24,bottom=24,right=24]",
    "elk.randomSeed": "1",
  } });
  for (const placed of layout.children ?? []) {
    const node = nodes.find(node => node.id === placed.id)!;
    node.position = { x: placed.x ?? 0, y: placed.y ?? 0 };
    node.data.ports = (placed.ports ?? []).map(port => {
      const x = port.x ?? 0, y = port.y ?? 0;
      const connection = [...connections.values()].find(edge => edge.sourceHandle === port.id || edge.targetHandle === port.id)!;
      return { id: port.id, type: connection.sourceHandle === port.id ? "source" : "target",
        side: x <= 0 ? Position.Left : x >= placed.width! ? Position.Right : y <= 0 ? Position.Top : Position.Bottom,
        x: x / placed.width! * 100, y: y / placed.height! * 100 };
    });
  }
  const routedEdges: Edge[] = (layout.edges ?? []).map(edge => {
    const section = edge.sections![0];
    const points = [section.startPoint, ...(section.bendPoints ?? []), section.endPoint];
    return { id: edge.id, ...connections.get(edge.id)!, type: "routed",
      data: { points, label: edge.labels?.[0] }, ariaLabel: edge.labels?.[0]?.text };
  });
  // Fit includes routing channels outside node bounds, including recursive connections.
  nodes.push({ id: "routing-bounds", type: "bounds", position: { x: 0, y: 0 },
    width: layout.width, height: layout.height, style: { width: layout.width, height: layout.height, opacity: 0, pointerEvents: "none" },
    data: {}, selectable: false, focusable: false, zIndex: -1, ariaLabel: "" });
  return { nodes, edges: routedEdges };
}
