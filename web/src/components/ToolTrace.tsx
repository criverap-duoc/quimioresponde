import { Wrench } from "lucide-react";

const LABELS: Record<string, string> = {
  search_regulation: "normativa",
  get_inventory: "inventario de ChemLab",
  get_chemical_info: "ficha de PubChem",
  check_storage_compatibility: "compatibilidad de almacenamiento",
};

type Props = { tools_called?: string[] };

export function ToolTrace({ tools_called = [] }: Props) {
  if (tools_called.length === 0) return null;
  const names = [...new Set(tools_called)];

  return (
    <details className="rounded-md border border-border bg-bg text-xs">
      <summary className="flex cursor-pointer flex-wrap items-center gap-1.5 px-2 py-1.5 text-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
        <Wrench className="size-3.5 shrink-0" aria-hidden="true" />
        <span>
          Consultó: <span className="text-fg">{names.map((name) => LABELS[name] ?? name).join(", ")}</span>
        </span>
      </summary>
      <ul className="space-y-0.5 border-t border-border px-3 py-2 font-mono text-muted">
        {names.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>
    </details>
  );
}
