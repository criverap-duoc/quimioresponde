import { AlertTriangle, ShieldAlert } from "lucide-react";

import type { RefusalTone } from "../lib/evidence";

const STYLES: Record<RefusalTone, { Icon: typeof ShieldAlert; label: string; tone: string }> = {
  danger: {
    Icon: ShieldAlert,
    label: "Sin evidencia verificable",
    tone: "border-danger/40 bg-danger/10 text-danger",
  },
  warning: {
    Icon: AlertTriangle,
    label: "Fuera del alcance del asistente",
    tone: "border-warning/40 bg-warning/10 text-warning",
  },
};

type Props = { reason: string; tone: RefusalTone };

export function RefusalCard({ reason, tone }: Props) {
  const { Icon, label, tone: styles } = STYLES[tone];

  return (
    <div role="note" className={`flex gap-2 rounded-lg border px-3 py-2 text-sm ${styles}`}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="space-y-0.5">
        <p className="font-medium">{label}</p>
        <p>{reason}</p>
      </div>
    </div>
  );
}
