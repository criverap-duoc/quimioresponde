import { SendHorizontal } from "lucide-react";

type Props = { value: string; onChange: (value: string) => void; onSubmit: () => void; disabled: boolean };

export function ChatInput({ value, onChange, onSubmit, disabled }: Props) {
  const canSend = !disabled && value.trim().length > 0;
  const submit = () => {
    if (canSend) onSubmit();
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className="rounded-lg border border-border bg-bg p-2 shadow-sm focus-within:border-accent focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent"
    >
      <label htmlFor="question" className="sr-only">
        Pregunta
      </label>
      <textarea
        id="question"
        name="question"
        rows={2}
        maxLength={1000}
        value={value}
        disabled={disabled}
        aria-describedby="question-hint"
        placeholder="Pregunta sobre normativa, almacenamiento o compatibilidad…"
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
          event.preventDefault();
          submit();
        }}
        className="field-sizing-content max-h-40 w-full resize-none bg-transparent px-1 py-1 text-sm text-fg placeholder:text-muted focus-visible:outline-none disabled:opacity-60"
      />
      <div className="flex flex-wrap items-center justify-between gap-2 px-1 pt-1">
        <p id="question-hint" className="text-xs text-muted">
          Enter envía · Shift+Enter salto de línea
        </p>
        <button type="submit" disabled={!canSend} className="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg transition-colors hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-60">
          <SendHorizontal className="size-4" aria-hidden="true" />
          {disabled ? "Respondiendo…" : "Enviar"}
        </button>
      </div>
    </form>
  );
}
