import { AlertTriangle, CircleCheck, CircleHelp, ShieldAlert } from "lucide-react";

type Severity = "INCOMPATIBLE" | "SEPARATE" | "COMPATIBLE" | "UNKNOWN";

const SEVERITY = /\b(INCOMPATIBLE|SEPARATE|COMPATIBLE|UNKNOWN)\b/i;
const SOURCE = /D\.\s?S\.\s?(?:N[°º]\s?)?43\s?\/\s?2015(?:[,\s]+Art(?:ículo)?\.?\s?\d+)?|OSHA[^.;\n]{0,40}|NFPA\s?400/gi;
const PAIR = /entre\s+(.{3,40}?)\s+y\s+(.{3,40}?)(?=\s+(?:es|son|no|debe|deben|reacciona|reaccionan)\b|[,.;:]|$)/i;
const SENTENCE = /(?<=[.!?])\s+(?![A-Za-zÁÉÍÓÚÑ]\.)|\n+/u;
const NEGATED = /no\s+(?:es|sería|resulta)\s*$/i;

const STYLES: Record<Severity, { Icon: typeof ShieldAlert; tone: string }> = {
  INCOMPATIBLE: { Icon: ShieldAlert, tone: "border-danger/40 bg-danger/10 text-danger" },
  SEPARATE: { Icon: AlertTriangle, tone: "border-warning/40 bg-warning/10 text-warning" },
  COMPATIBLE: { Icon: CircleCheck, tone: "border-success/40 bg-success/10 text-success" },
  UNKNOWN: { Icon: CircleHelp, tone: "border-border bg-bg text-muted" },
};

function parse(text: string) {
  // El agente responde en prosa: la frase de severidad y las fuentes citadas se leen del texto.
  const mentions = [...text.matchAll(new RegExp(SEVERITY.source, "gi"))];
  const mention = mentions.find((match) => {
    const before = text.slice(Math.max(0, (match.index ?? 0) - 16), match.index);
    return !NEGATED.test(before);
  });
  const phrase = text.split(SENTENCE).find((part) => SEVERITY.test(part)) ?? text.trim();
  const pair = PAIR.exec(phrase);
  return {
    severity: (mention?.[1] ?? "UNKNOWN").toUpperCase() as Severity,
    rules: [...new Set(text.match(SOURCE) ?? [])].slice(0, 3).map((source) => ({
      pair: pair ? `${pair[1].trim()} / ${pair[2].trim()}` : null,
      reason: phrase.trim(),
      source,
    })),
  };
}

export function CompatibilityCard({ text }: { text: string }) {
  const { severity, rules } = parse(text);
  const { Icon, tone } = STYLES[severity];
  return (
    <section aria-label="Resultado de compatibilidad" className="space-y-2 rounded-lg border border-border px-3 py-2">
      <p className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-semibold ${tone}`}>
        <Icon className="size-3.5" aria-hidden="true" />{severity}
      </p>
      {rules.length > 0 && (
        <ul className="space-y-1.5">
          {rules.map((rule) => (
            <li key={rule.source} className="space-y-0.5 rounded-md border border-border px-2 py-1.5">
              <p className="flex flex-wrap items-baseline gap-x-2 text-xs">
                {rule.pair && <span className="font-semibold text-fg">{rule.pair}</span>}
                <span className="text-muted">Fuente: {rule.source}</span>
              </p>
              <p className="text-sm text-fg">{rule.reason}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
