import { useEffect, useState } from "react";
import { BaseEdge, Controls, Handle, ReactFlow, type EdgeProps, type NodeProps } from "@xyflow/react";
import { toDiagram, type Diagram, type DiagramPort } from "./diagram";
import type { ERSchema } from "./types";
function NodePorts({ ports }: { ports: DiagramPort[] }) {
  return ports.map(port => <Handle key={port.id} id={port.id} type={port.type}
    position={port.side} style={{ left: `${port.x}%`, top: `${port.y}%`, transform: "translate(-50%, -50%)" }} />);
}
function EntityNode({ data }: NodeProps) {
  const fields = data.fields as ERSchema["entities"][number]["attributes"];
  return <>
    <NodePorts ports={data.ports as DiagramPort[]} />
    <div className="entity-title">{data.title as string}</div>
    <div className="entity-fields">{fields.map((field, i) => <div className="entity-field" key={i}>
      <span className="field-symbol" aria-label={field.is_identifier ? "Identificador" : undefined}>{field.is_identifier ? "◆" : "·"}</span>
      <span>{field.name}</span><small>{field.data_type}</small>
    </div>)}</div>
  </>;
}
function RelationshipNode({ data }: NodeProps) {
  return <>
    <svg className="relationship-shape" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <polygon points="0,50 50,0 100,50 50,100" />
    </svg>
    <div className="relationship-name">{data.label as string}</div>
    <NodePorts ports={data.ports as DiagramPort[]} />
  </>;
}
function RoutedEdge({ id, data }: EdgeProps) {
  const points = data?.points as { x: number; y: number }[];
  const label = data?.label as { x: number; y: number; width: number; height: number; text: string } | undefined;
  const path = points.map((point, i) => `${i ? "L" : "M"} ${point.x} ${point.y}`).join(" ");
  return <>
    <BaseEdge id={id} path={path} />
    {label && <g className="cardinality-label" transform={`translate(${label.x}, ${label.y})`}>
      <rect x={-3} y={-1} width={label.width + 6} height={label.height + 2} rx={2} />
      <text x={label.width / 2} y={label.height / 2} dominantBaseline="central" textAnchor="middle">{label.text}</text>
    </g>}
  </>;
}
const nodeTypes = { default: EntityNode, relationship: RelationshipNode, bounds: () => null };
const edgeTypes = { routed: RoutedEdge };
export function DiagramView({ schema, compact, colorMode }: { schema: ERSchema; compact: boolean; colorMode: "light" | "dark" }) {
  const [diagram, setDiagram] = useState<Diagram | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    setDiagram(null);
    setFailed(false);
    toDiagram(schema, compact).then(graph => { if (active) setDiagram(graph); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [schema, compact]);
  if (failed) return <p role="alert" className="error">Não foi possível organizar o diagrama. Abra a geração novamente para tentar.</p>;
  if (!diagram) return <div className="empty" role="status">Organizando diagrama…</div>;
  return <ReactFlow nodes={diagram.nodes} edges={diagram.edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes}
    fitView fitViewOptions={{ padding: { top: "24px", right: "24px", bottom: "76px", left: "24px" }, minZoom: 0.01, maxZoom: 1.1 }}
    minZoom={0.01} nodesConnectable={false} nodesDraggable={false} colorMode={colorMode}>
    <Controls showInteractive={false} fitViewOptions={{ padding: 0.15, minZoom: 0.01, maxZoom: 1.1 }} />
  </ReactFlow>;
}
