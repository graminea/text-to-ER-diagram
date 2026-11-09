import { useEffect, useRef, useState, type CSSProperties } from "react";

const presets = [
  ["Branco", "#f5f5f5"],
  ["Prata", "#b8bec7"],
  ["Azul", "#497cf3"],
  ["Celeste", "#55aaff"],
  ["Ciano", "#39c8d7"],
  ["Petróleo", "#389a9a"],
  ["Verde", "#50b78b"],
  ["Oliva", "#a5b56a"],
  ["Lima", "#c1d963"],
  ["Amarelo", "#ebce61"],
  ["Âmbar", "#e4ac52"],
  ["Laranja", "#ef9257"],
  ["Terracota", "#cb816b"],
  ["Coral", "#ed837c"],
  ["Vermelho", "#e66168"],
  ["Rosa", "#df8eaf"],
  ["Magenta", "#c877b9"],
  ["Ameixa", "#a879b8"],
  ["Violeta", "#8f83d1"],
  ["Índigo", "#798bca"],
] as const;
const bases = [
  ["Preto", "#0a0a0a"],
  ["Carvão", "#171717"],
  ["Ardósia", "#151a22"],
  ["Papel", "#f3f3f0"],
  ["Branco", "#ffffff"],
] as const;
const defaults = { accent: "#f5f5f5", background: "#0a0a0a", extended: false };
type Appearance = typeof defaults;
const storageKey = "schemapilot-appearance";
const hex = /^#[\da-f]{6}$/i;
function luminance(color: string) {
  const channels = color
    .slice(1)
    .match(/../g)!
    .map((c) => parseInt(c, 16) / 255)
    .map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}
function foreground(color: string) {
  return luminance(color) > 0.179 ? "#000000" : "#ffffff";
}
function mutedForeground(background: string) {
  const target = foreground(background) === "#ffffff" ? 255 : 0;
  for (let weight = 0.65; weight < 1; weight += 0.05) {
    const candidate =
      "#" +
      background
        .slice(1)
        .match(/../g)!
        .map((channel) =>
          Math.round(parseInt(channel, 16) * (1 - weight) + target * weight)
            .toString(16)
            .padStart(2, "0"),
        )
        .join("");
    const values = [luminance(background), luminance(candidate)].sort(
      (a, b) => a - b,
    );
    if ((values[1] + 0.05) / (values[0] + 0.05) >= 4.5) return candidate;
  }
  return foreground(background);
}
function readAppearance(): Appearance {
  try {
    const saved: unknown = JSON.parse(
      localStorage.getItem(storageKey) ?? "null",
    );
    if (
      saved &&
      typeof saved === "object" &&
      "accent" in saved &&
      "background" in saved &&
      "extended" in saved &&
      typeof saved.accent === "string" &&
      hex.test(saved.accent) &&
      typeof saved.background === "string" &&
      hex.test(saved.background) &&
      typeof saved.extended === "boolean"
    )
      return saved as Appearance;
  } catch {
    /* Storage is optional. */
  }
  return defaults;
}
export function useAppearance() {
  const [appearance, setAppearance] = useState(readAppearance);
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(appearance));
    } catch {
      /* Storage is optional. */
    }
  }, [appearance]);
  const light = foreground(appearance.background) === "#000000";
  const style = {
    "--bg": appearance.background,
    "--fg": foreground(appearance.background),
    "--muted": mutedForeground(appearance.background),
    "--accent": appearance.accent,
    "--on-accent": foreground(appearance.accent),
    "--node-accent": appearance.extended
      ? appearance.accent
      : light
        ? "#565656"
        : "#aaa",
    colorScheme: light ? "light" : "dark",
  } as CSSProperties;
  return { appearance, setAppearance, style };
}
function ColorField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  return (
    <div className="color-field">
      <span>{label}</span>
      <input
        type="color"
        aria-label={`${label}: seletor`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <input
        className="hex-input"
        aria-label={`${label}: hexadecimal`}
        value={draft}
        maxLength={7}
        spellCheck={false}
        aria-invalid={!hex.test(draft)}
        onBlur={() => setDraft(value)}
        onChange={(e) => {
          setDraft(e.target.value);
          if (hex.test(e.target.value)) onChange(e.target.value);
        }}
      />
    </div>
  );
}
export function AppearanceExplorer({
  appearance,
  setAppearance,
}: {
  appearance: Appearance;
  setAppearance: (value: Appearance) => void;
}) {
  const dialog = useRef<HTMLDivElement>(null);
  const update = (patch: Partial<Appearance>) =>
    setAppearance({ ...appearance, ...patch });
  const name =
    presets.find(([, color]) => color === appearance.accent)?.[0] ??
    "Personalizado";
  return (
    <>
      <button
        className="appearance-trigger"
        popoverTarget="appearance-explorer"
        aria-haspopup="dialog"
      >
        <span style={{ background: appearance.accent }} />
        Cores
      </button>
      <div
        id="appearance-explorer"
        popover="auto"
        role="dialog"
        className="appearance-dialog"
        ref={dialog}
        aria-labelledby="appearance-title"
      >
        <div className="appearance-header">
          <h2 id="appearance-title">Aparência</h2>
          <button
            autoFocus
            aria-label="Fechar aparência"
            onClick={() => dialog.current?.hidePopover()}
          >
            ×
          </button>
        </div>
        <p className="appearance-intro">
          Compare as cores no workspace. As mudanças são salvas neste navegador.
        </p>
        <fieldset>
          <legend>
            Destaque <span>{name}</span>
          </legend>
          <div className="swatches">
            {presets.map(([label, color]) => (
              <button
                key={label}
                className="swatch"
                aria-label={label}
                title={label}
                aria-pressed={appearance.accent === color}
                onClick={() => update({ accent: color })}
              >
                <span style={{ background: color }} />
                {label}
              </button>
            ))}
          </div>
        </fieldset>
        <ColorField
          label="Cor de destaque"
          value={appearance.accent}
          onChange={(accent) => update({ accent })}
        />
        <fieldset>
          <legend>Superfície</legend>
          <div className="base-options">
            {bases.map(([label, color]) => (
              <button
                key={label}
                aria-pressed={appearance.background === color}
                onClick={() => update({ background: color })}
              >
                <span style={{ background: color }} />
                {label}
              </button>
            ))}
          </div>
        </fieldset>
        <ColorField
          label="Cor de fundo"
          value={appearance.background}
          onChange={(background) => update({ background })}
        />
        <label className="accent-scope">
          <input
            type="checkbox"
            checked={appearance.extended}
            onChange={(e) => update({ extended: e.target.checked })}
          />
          Aplicar destaque também ao diagrama
        </label>
        <div className="appearance-footer">
          <button onClick={() => setAppearance(defaults)}>
            Restaurar preto e branco
          </button>
          <button
            className="primary"
            onClick={() => dialog.current?.hidePopover()}
          >
            Concluir
          </button>
        </div>
      </div>
    </>
  );
}
