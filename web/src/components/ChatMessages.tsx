import { AlertTriangle, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { Citation, ProblemDetail } from "../lib/api";
import { refusalTone, type EvidenceSource } from "../lib/evidence";
import { CitationBadge } from "./CitationBadge";
import { CompatibilityCard } from "./CompatibilityCard";
import { RefusalCard } from "./RefusalCard";
import { ToolTrace } from "./ToolTrace";

export type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations: Citation[];
  tools_called?: string[];
  evidence_source?: EvidenceSource;
  refusal_reason?: string | null;
};

const MARKER = /\[(\d+)\]/g;

const REFUSAL_DETAILS: Record<string, string> = {
  no_citations: "No se encontró evidencia citable en el corpus para esta pregunta.",
  unverifiable_quote: "La respuesta no coincidía literalmente con el artículo citado.",
  unknown_chunk: "La cita apuntaba a un fragmento que no pertenece al corpus.",
  refusal_with_citations: "La respuesta mezclaba un rechazo con citas; se descartó.",
};

type Props = { messages: Message[]; problem: ProblemDetail | null; streaming: boolean };

const FOCUS = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

function renderAnswer(
  message: Message,
  openKey: string | null,
  setOpenKey: (key: string | null) => void,
): ReactNode[] {
  const parts: ReactNode[] = [];
  let cursor = 0;
  for (const match of message.text.matchAll(MARKER)) {
    const position = Number(match[1]);
    const citation = message.citations[position - 1];
    if (!citation) continue;
    const key = `${message.id}:${position}`;
    parts.push(message.text.slice(cursor, match.index));
    parts.push(
      <button
        key={key}
        type="button"
        title={citation.quote}
        onClick={() => setOpenKey(openKey === key ? null : key)}
        className={`mx-0.5 rounded bg-accent/10 px-1 align-baseline text-xs font-semibold text-accent ${FOCUS}`}
      >
        [{position}]
      </button>,
    );
    cursor = match.index + match[0].length;
  }
  parts.push(message.text.slice(cursor));
  return parts;
}

function ProblemAlert({ problem }: { problem: ProblemDetail }) {
  const refusal = problem.type === "citation_rejected";
  const Icon = refusal ? ShieldAlert : AlertTriangle;
  const detail = refusal
    ? (REFUSAL_DETAILS[String(problem.detail)] ?? "Respuesta sin citas verificables; no se entrega.")
    : typeof problem.detail === "string" && problem.detail
      ? problem.detail
      : problem.title;
  const tone = refusal
    ? "border-warning/40 bg-warning/10 text-warning"
    : "border-danger/40 bg-danger/10 text-danger";

  return (
    <div role="alert" className={`flex gap-2 rounded-lg border px-3 py-2 text-sm ${tone}`}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="space-y-0.5">
        <p className="font-medium">{refusal ? "Sin evidencia verificable" : problem.title}</p>
        <p>{detail}</p>
      </div>
    </div>
  );
}

export function ChatMessages({ messages, problem, streaming }: Props) {
  const [openKey, setOpenKey] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, problem]);

  return (
    <div className="space-y-4" aria-live="polite" aria-busy={streaming}>
      {messages.map((message, position) => {
        if (message.role === "user") {
          return (
            <div key={message.id} className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl bg-accent px-3 py-2 text-sm whitespace-pre-wrap text-accent-fg">
                <span className="sr-only">Pregunta: </span>
                {message.text}
              </p>
            </div>
          );
        }
        if (message.text === "" && message.citations.length === 0 && !streaming) return null;
        const refusal = message.evidence_source === "none" && Boolean(message.refusal_reason);
        return (
          <div key={message.id} className="space-y-2 rounded-lg border border-border px-3 py-2">
            <h2 className="sr-only">Respuesta del asistente</h2>
            {refusal ? (
              <RefusalCard reason={message.refusal_reason ?? ""} tone={refusalTone(message.refusal_reason ?? "")} />
            ) : (
              <div className="text-sm leading-relaxed whitespace-pre-wrap text-fg">
                {renderAnswer(message, openKey, setOpenKey)}
                {streaming && position === messages.length - 1 && (
                  <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-fg align-text-bottom" aria-hidden="true" />
                )}
              </div>
            )}
            {message.evidence_source === "compatibility" && <CompatibilityCard text={message.text} />}
            {message.citations.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium tracking-wide text-muted uppercase">Fuentes citadas</p>
                {message.citations.map((citation, index) => {
                  const key = `${message.id}:${index + 1}`;
                  return (
                    <CitationBadge
                      key={key}
                      index={index + 1}
                      citation={citation}
                      expanded={openKey === key}
                      onToggle={(expanded) => setOpenKey(expanded ? key : null)}
                    />
                  );
                })}
              </div>
            )}
            <ToolTrace tools_called={message.tools_called} />
          </div>
        );
      })}
      {problem && <ProblemAlert problem={problem} />}
      <div ref={endRef} />
    </div>
  );
}

