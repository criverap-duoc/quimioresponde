import { useEffect, useRef, useState } from "react";

import { ChatInput } from "./components/ChatInput";
import { ChatMessages, type Message } from "./components/ChatMessages";
import { ColdStartSkeleton } from "./components/ColdStartSkeleton";
import { EmptyState } from "./components/EmptyState";
import { Footer } from "./components/Footer";
import { streamChat, type ProblemDetail } from "./lib/api";
import { classifyAnswer } from "./lib/evidence";

type Status = "idle" | "streaming" | "error";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const cancel = () => abortRef.current?.abort();
    window.addEventListener("pagehide", cancel);
    return () => {
      window.removeEventListener("pagehide", cancel);
      cancel();
    };
  }, []);

  function updateAssistant(patch: (message: Message) => Message) {
    setMessages((current) => {
      const last = current.at(-1);
      if (!last || last.role !== "assistant") return current;
      return [...current.slice(0, -1), patch(last)];
    });
  }

  async function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || abortRef.current) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("streaming");
    setProblem(null);
    setDraft("");
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: trimmed, citations: [] },
      { id: crypto.randomUUID(), role: "assistant", text: "", citations: [] },
    ]);

    try {
      for await (const event of streamChat(trimmed, controller.signal)) {
        if (event.type === "citations") {
          const citations = event.data;
          updateAssistant((message) => ({ ...message, citations }));
        } else if (event.type === "answer") {
          const delta = event.data;
          updateAssistant((message) => ({ ...message, text: message.text + delta }));
        } else if (event.type === "error") {
          setProblem(event.data);
          setStatus("error");
        } else {
          const toolsCalled = event.tools_called;
          updateAssistant((message) => ({
            ...message,
            tools_called: toolsCalled,
            ...classifyAnswer(message.text, message.citations, toolsCalled),
          }));
          setStatus("idle");
        }
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setProblem({
          type: "network_error",
          title: "No se pudo consultar la API",
          status: 0,
          detail: error instanceof Error ? error.message : String(error),
        });
        setStatus("error");
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setStatus((current) => (current === "streaming" ? "idle" : current));
    }
  }

  const last = messages.at(-1);
  const awaitingFirstToken =
    status === "streaming" && last?.role === "assistant" && last.text === "";

  return (
    <div className="flex h-dvh flex-col">
      <header className="border-b border-border px-4 py-3">
        <div className="mx-auto w-full max-w-3xl">
          <h1 className="text-lg font-semibold text-fg">QuimioResponde</h1>
          <p className="text-sm text-muted">Asistente referencial de seguridad química · Chile</p>
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-3 px-4 py-4">
        <div className="min-h-0 flex-1 overflow-y-auto">
          {messages.length === 0 && <EmptyState onPick={setDraft} />}
          <ChatMessages messages={messages} problem={problem} streaming={status === "streaming"} />
          {awaitingFirstToken && (
            <div className="mt-4">
              <ColdStartSkeleton />
            </div>
          )}
        </div>
        <ChatInput
          value={draft}
          onChange={setDraft}
          onSubmit={() => void ask(draft)}
          disabled={status === "streaming"}
        />
      </main>
      <Footer />
    </div>
  );
}
