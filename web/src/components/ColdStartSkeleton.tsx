import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

const COLD_START_DELAY_MS = 3000;

export function ColdStartSkeleton() {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), COLD_START_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, []);

  if (!slow) return null;

  return (
    <div role="status" className="space-y-2 rounded-lg border border-border px-3 py-3">
      <p className="flex items-center gap-2 text-sm text-muted">
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        Despertando el servidor; la primera respuesta puede tardar unos segundos.
      </p>
      <div className="h-3 w-3/4 animate-pulse rounded bg-border" aria-hidden="true" />
      <div className="h-3 w-full animate-pulse rounded bg-border" aria-hidden="true" />
      <div className="h-3 w-2/3 animate-pulse rounded bg-border" aria-hidden="true" />
    </div>
  );
}
