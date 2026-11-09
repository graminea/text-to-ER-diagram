export type Participation = {
  entity: string;
  role: string;
  min_cardinality: 0 | 1;
  max_cardinality: 1 | 'N';
};
export type ERSchema = {
  entities: { name: string; attributes: {
    name: string;
    data_type: 'string' | 'integer' | 'decimal' | 'boolean' | 'date' | null;
    is_identifier: boolean;
  }[] }[];
  relationships: { name: string; participants: [Participation, Participation] }[];
  assumptions: string[];
  ambiguities: string[];
};
export type GenerationFlow = "A" | "B";
export type Generation = {
  flow?: string;
  model?: string | null;
  prompt_version?: string | null;
  output_mode?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  call_count?: number | null;
  total_latency_ms?: number | null;
  specialist_findings?: { consistency: string[]; cardinality: string[] } | null;
  id: string;
  created_at: string;
  requirements: string;
  provider: string;
  latency_ms: number;
  schema_model: ERSchema;
  validation: { valid: boolean; issues: {
    code: string; path: string; message: string; severity: 'error' | 'warning';
  }[] };
};

export type Health = {
  status: string;
  provider: string;
  mode: 'custom' | 'llm';
  model: string | null;
};
