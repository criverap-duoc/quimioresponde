import { FlaskConical, MessageSquarePlus, Wind } from "lucide-react";

const EXAMPLES = [
  { Icon: FlaskConical, question: "¿Cuál es la distancia mínima entre cilindros de gas inflamable y materiales comburentes?" },
  { Icon: MessageSquarePlus, question: "¿Qué incompatibilidades de almacenamiento aplican a oxidantes y combustibles?" },
  { Icon: Wind, question: "¿Qué requisitos de ventilación se exigen en un almacén de sustancias peligrosas?" },
];

type Props = { onPick: (question: string) => void };

export function EmptyState({ onPick }: Props) {
  return (
    <section className="space-y-4 py-6">
      <div className="space-y-1">
        <h2 className="text-base font-semibold text-fg">Consulta la normativa con citas literales</h2>
        <p className="text-sm text-muted">
          Cada respuesta cita el artículo del que sale. Si el corpus no lo cubre, la respuesta es «no encontrado». Resultado referencial, no un dictamen.
        </p>
      </div>
      <ul className="grid gap-2 sm:grid-cols-3">
        {EXAMPLES.map(({ Icon, question }) => (
          <li key={question}>
            <button type="button" onClick={() => onPick(question)} className="flex h-full w-full flex-col items-start gap-2 rounded-lg border border-border px-3 py-3 text-left text-sm text-fg transition-colors hover:border-accent hover:bg-accent/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              <Icon className="size-4 text-accent" aria-hidden="true" />
              {question}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
