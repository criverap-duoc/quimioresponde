/** Deduce la evidencia declarada por el agente a partir de lo que llega por SSE. */

import type { Citation } from "./api";

export type EvidenceSource = "regulation" | "inventory" | "pubchem" | "compatibility" | "none";
export type RefusalTone = "danger" | "warning";

const TOOL_SOURCES: Record<string, EvidenceSource> = {
  search_regulation: "regulation",
  get_inventory: "inventory",
  get_chemical_info: "pubchem",
  check_storage_compatibility: "compatibility",
};

// El SSE solo transporta `tools_called`: el rechazo se reconoce por su texto y la falta de citas.
const REFUSAL =
  /\bno (?:puedo|es posible|dispongo|cuento con)\b|sin evidencia|fuera de alcance|no (?:se )?encontr[oé][^.]{0,80}(?:evidencia|corpus)/i;
const DICTAMEN = /dictamen|dictamin|certificaci|cumplimiento|alcance/i;

export function classifyAnswer(
  text: string,
  citations: Citation[],
  toolsCalled: string[],
): { evidence_source: EvidenceSource; refusal_reason: string | null } {
  const source = toolsCalled.map((name) => TOOL_SOURCES[name]).find(Boolean);
  if (source === "compatibility") return { evidence_source: source, refusal_reason: null };
  if (citations.length > 0) return { evidence_source: "regulation", refusal_reason: null };
  if (REFUSAL.test(text)) return { evidence_source: "none", refusal_reason: text.trim() };
  return { evidence_source: source ?? "none", refusal_reason: null };
}

export function refusalTone(reason: string): RefusalTone {
  return DICTAMEN.test(reason) ? "warning" : "danger";
}
