import { ExternalLink } from "lucide-react";

import type { Citation } from "../lib/api";

const PREVIEW_LENGTH = 140;

type Props = { index: number; citation: Citation; expanded: boolean; onToggle: (expanded: boolean) => void };

function preview(quote: string): string {
  const clean = quote.replace(/\s+/g, " ").trim();
  return clean.length > PREVIEW_LENGTH ? `${clean.slice(0, PREVIEW_LENGTH - 1)}…` : clean;
}

export function CitationBadge({ index, citation, expanded, onToggle }: Props) {
  const label = citation.article ? `Artículo ${citation.article}` : "Fragmento citado";

  return (
    <details open={expanded} onToggle={(event) => onToggle(event.currentTarget.open)} className="rounded-md border border-border bg-bg">
      <summary title={preview(citation.quote)} className="flex cursor-pointer flex-wrap items-center gap-2 px-2 py-1.5 text-sm text-fg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
        <span className="rounded bg-accent/10 px-1.5 font-semibold text-accent">[{index}]</span>
        <span className="font-medium">{label}</span>
        <span className="text-xs text-muted">cita verificada</span>
      </summary>
      <div className="space-y-2 border-t border-border px-3 py-2">
        <blockquote className="border-l-2 border-accent pl-2 text-sm text-fg">«{citation.quote.trim()}»</blockquote>
        {citation.url ? (
          <a href={citation.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-medium text-accent underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
            Ver artículo completo
            <ExternalLink className="size-3.5" aria-hidden="true" />
          </a>
        ) : (
          <p className="text-xs text-muted">El servidor no informó la URL del artículo.</p>
        )}
      </div>
    </details>
  );
}
