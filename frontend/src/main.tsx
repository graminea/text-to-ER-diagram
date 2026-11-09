import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "@xyflow/react/dist/style.css";
import "./style.css";
import { DiagramView } from "./DiagramView";
import { AppearanceExplorer, useAppearance } from "./appearance";
import type { Generation, GenerationFlow, Health } from "./types";

const exampleRequirements =
  "Um cliente pode fazer vários pedidos. Cada pedido pertence a exatamente um cliente.";
const flowLabels = { A: "Direta", B: "Com agentes" };
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    const messages: Record<string, string> = {
      authentication: "O provedor rejeitou a chave ou suas permissões. Verifique a configuração no backend.",
      rate_limit: "O provedor atingiu um limite de uso. Verifique sua cota e tente novamente.",
      timeout: "O provedor demorou demais para responder. Tente novamente.",
      unsupported: "O modelo não aceita esta configuração de saída. Verifique o modelo e o formato no backend.",
      refusal: "O provedor recusou a geração. Revise os requisitos e tente novamente.",
      truncated: "A resposta ficou incompleta. Aumente o limite de saída no backend.",
      invalid_output: "A resposta não corresponde ao formato ER esperado. Tente novamente.",
      connection: "Não foi possível conectar ao provedor. Confira a conexão e tente novamente.",
      provider_unavailable: "O provedor está indisponível. Tente novamente em alguns minutos.",
    };
    const body = await response.json().catch(() => null);
    const code = body?.detail?.code;
    throw new Error(
      (typeof code === "string" && messages[code]) || (response.status === 502 || response.status === 504
        ? "O gerador não conseguiu produzir um modelo ER válido. Tente novamente."
        : `Não foi possível concluir a operação (${response.status}). Verifique a API.`),
    );
  }
  return response.json() as Promise<T>;
}
function App() {
  const { appearance, setAppearance, style } = useAppearance();
  const [requirements, setRequirements] = useState(exampleRequirements);
  const [flow, setFlow] = useState<GenerationFlow>("A");
  const [result, setResult] = useState<Generation | null>(null);
  const [history, setHistory] = useState<Generation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [compact, setCompact] = useState(
    () => window.matchMedia("(max-width: 1000px)").matches,
  );
  useEffect(() => {
    const media = window.matchMedia("(max-width: 1000px)");
    const update = () => setCompact(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    api<Health>("/health").then(setHealth).catch(() => setHealth(null));
    api<Generation[]>("/generations")
      .then(setHistory)
      .catch(() =>
        setError("API indisponível. Inicie o backend e recarregue a página."),
      );
  }, []);
  async function generate() {
    setBusy(true);
    setError("");
    try {
      const next = await api<Generation>("/generations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirements, flow }),
      });
      setResult(next);
      setHistory((current) => [next, ...current].slice(0, 20));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha na geração.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="app" style={style}>
      <header className="project-bar">
        <a className="brand" href="/" aria-label="Text to ER, início">
          Text to ER
        </a>
        <div className="header-actions">
          <AppearanceExplorer
            appearance={appearance}
            setAppearance={setAppearance}
          />
        </div>
      </header>
      <main className="workbench">
        <section className="editor-pane" aria-labelledby="editor-heading">
          <h1 id="editor-heading">Requisitos</h1>
          <label className="sr-only" htmlFor="requirements">
            Requisitos do sistema
          </label>
          <textarea
            id="requirements"
            value={requirements}
            maxLength={10000}
            spellCheck={false}
            onChange={(e) => setRequirements(e.target.value)}
            rows={9}
          />
          <div className="generation-actions">
            <label htmlFor="generation-flow">Tipo de geração</label>
            <select
              id="generation-flow"
              aria-describedby={flow === "B" ? "agent-token-note" : undefined}
              value={flow}
              disabled={busy}
              onChange={(e) => setFlow(e.target.value as GenerationFlow)}
            >
              <option value="A">{flowLabels.A}</option>
              <option value="B">{flowLabels.B}</option>
            </select>
            <button
              className="primary"
              disabled={busy || requirements.trim().length < 10}
              onClick={generate}
            >
              {busy ? "Gerando modelo…" : "Gerar diagrama"}
            </button>
          </div>
          {(flow === "B" || health?.model) && (
            <p className="model-note">
              {flow === "B" && (
                <span id="agent-token-note">Com agentes, a geração tende a usar mais tokens.</span>
              )}
              {health?.model && <span>Modelo: {health.model}</span>}
            </p>
          )}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <details className="history">
            <summary>
              Gerações recentes <span>{history.length}</span>
            </summary>
            {history.length === 0 && (
              <p className="history-empty">Nenhuma geração ainda.</p>
            )}
            <div className="history-list">
              {history.map((item) => (
                <button
                  key={item.id}
                  className={`history-item ${result?.id === item.id ? "active" : ""}`}
                  aria-pressed={result?.id === item.id}
                  onClick={() => {
                    setResult(item);
                    setRequirements(item.requirements);
                  }}
                >
                  <span>{item.requirements}</span>
                  <small>
                    {new Date(item.created_at).toLocaleString("pt-BR")}
                  </small>
                </button>
              ))}
            </div>
          </details>
        </section>
        <section
          className="model-pane"
          aria-labelledby="model-heading"
          aria-busy={busy}
        >
          <div className="model-heading">
            <h2 id="model-heading">Modelo ER</h2>
            {result && (
              <span
                className={`validation-status ${result.validation.valid ? "" : "invalid"}`}
              >
                <svg viewBox="0 0 16 16" aria-hidden="true">
                  {result.validation.valid ? (
                    <path d="m3 8 3 3 7-7" />
                  ) : (
                    <path d="M8 2 15 14H1L8 2Zm0 4v3m0 2v.5" />
                  )}
                </svg>
                {result.validation.valid
                  ? "Estrutura válida"
                  : "Requer correções"}
              </span>
            )}
          </div>
          <div className="canvas" aria-label="Diagrama ER">
            {result ? (
              <DiagramView key={`${result.id}-${compact}`} schema={result.schema_model}
                compact={compact} colorMode={style.colorScheme === "light" ? "light" : "dark"} />
            ) : (
              <div className="empty">
                <h2>Nenhum modelo</h2>
                <p>Descreva o domínio e gere o diagrama.</p>
              </div>
            )}
            {busy && (
              <div className="generation-overlay" role="status">
                Construindo o modelo…
              </div>
            )}
          </div>
          {result && (
            <div className="model-review">
              {result.validation.issues.map((issue, i) => (
                <p
                  key={i}
                  className={issue.severity === "error" ? "error" : "warning"}
                >
                  {issue.severity === "error" ? "Erro" : "Atenção"}:{" "}
                  {issue.message}
                </p>
              ))}
              <details className="report" key={result.id}>
                <summary>Decisões e validação</summary>
                <div className="report-content">
                  <p className="validation-note">
                    Validade estrutural não garante fidelidade aos requisitos ou
                    aprovação humana.
                  </p>
                  {result.schema_model.assumptions.length > 0 && (
                    <div className="decision-group">
                      <h3>Premissas</h3>
                      {result.schema_model.assumptions.map((text, i) => (
                        <p key={i}>{text}</p>
                      ))}
                    </div>
                  )}
                  {result.schema_model.ambiguities.length > 0 && (
                    <div className="decision-group">
                      <h3>Ambiguidades</h3>
                      {result.schema_model.ambiguities.map((text, i) => (
                        <p key={i}>{text}</p>
                      ))}
                    </div>
                  )}
                  {result.specialist_findings && (
                    <div className="decision-group specialist-findings">
                      <h3>Pareceres sobre o rascunho</h3>
                      <dl>
                        {([
                          ["Coerência", result.specialist_findings.consistency],
                          ["Cardinalidade", result.specialist_findings.cardinality],
                        ] as const).map(([role, findings]) => (
                          <div key={role}>
                            <dt>{role}</dt>
                            <dd>
                              {findings.length ? (
                                <ul>
                                  {findings.map((finding, i) => <li key={i}>{finding}</li>)}
                                </ul>
                              ) : "Nenhum achado."}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  )}
                  <details className="json-view">
                    <summary>Ver JSON canônico</summary>
                    <pre>{JSON.stringify(result.schema_model, null, 2)}</pre>
                  </details>
                  <p className="provider-info">
                    {result.flow === "B" && `${flowLabels.B} / `}
                    {result.flow === "A" && result.call_count === 1 && `${flowLabels.A} / `}
                    {result.provider}{result.model ? ` / ${result.model}` : ""} / {result.total_latency_ms ?? result.latency_ms} ms
                    {result.input_tokens != null && ` / ${result.input_tokens} tokens de entrada`}
                    {result.output_tokens != null && ` / ${result.output_tokens} tokens de saída`}
                  </p>
                </div>
              </details>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
