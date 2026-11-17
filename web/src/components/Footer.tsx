const LEY_CHILE_URL = "https://www.bcn.cl/leychile/";

export function Footer() {
  const consulted = new Date().toISOString().slice(0, 10);

  return (
    <footer className="border-t border-border px-4 py-4">
      <p className="mx-auto w-full max-w-3xl text-xs leading-relaxed text-muted">
        Fuente:{" "}
        <a
          href={LEY_CHILE_URL}
          target="_blank"
          rel="noreferrer"
          className="underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Ley Chile – Biblioteca del Congreso Nacional
        </a>
        . Consultado el {consulted}. Resultado referencial; no constituye interpretación oficial.
      </p>
    </footer>
  );
}
