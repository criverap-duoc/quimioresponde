/** Cliente SSE mínimo para `POST /chat`, sin librerías de terceros. */

export type Citation = { chunk_id: string; quote: string; article?: string; url?: string };

export type ProblemDetail = { type: string; title: string; status: number; detail: unknown; instance?: string };

export type ChatEvent =
  | { type: "citations"; data: Citation[] }
  | { type: "answer"; data: string }
  | { type: "done"; tools_called: string[] }
  | { type: "error"; data: ProblemDetail };

const BASE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export async function* streamChat(
  question: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!response.ok || response.body === null) {
    yield { type: "error", data: await problemFromResponse(response) };
    return;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const event = parseEvent(block);
        if (event) yield event;
      }
    }
    const pending = parseEvent(buffer);
    if (pending) yield pending;
  } finally {
    await reader.cancel().catch(() => undefined);
  }
}

function parseEvent(block: string): ChatEvent | null {
  let name = "message";
  const data: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    if (field === "event") name = line.slice(colon + 1).trim();
    else if (field === "data") data.push(line.slice(colon + 1).replace(/^ /, ""));
  }
  const payload = data.join("\n");
  if (name === "citations") return { type: "citations", data: JSON.parse(payload) as Citation[] };
  if (name === "answer") return { type: "answer", data: payload };
  if (name === "done") return { type: "done", tools_called: toolsCalled(payload) };
  if (name === "error") return { type: "error", data: JSON.parse(payload) as ProblemDetail };
  return null;
}

function toolsCalled(payload: string): string[] {
  try {
    const parsed = JSON.parse(payload) as { tools_called?: unknown };
    return Array.isArray(parsed.tools_called)
      ? parsed.tools_called.filter((name): name is string => typeof name === "string")
      : [];
  } catch {
    return [];
  }
}

async function problemFromResponse(response: Response): Promise<ProblemDetail> {
  try {
    return (await response.json()) as ProblemDetail;
  } catch {
    const detail = response.statusText || "No se pudo leer el cuerpo del error.";
    return { type: "unexpected_response", title: "Respuesta inesperada", status: response.status, detail };
  }
}

