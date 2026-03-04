/**
 * Servicio de chat — conexión SSE con el backend ChatTeamsAgent.
 */
import type { ChatEvent } from "../types/chat";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

/**
 * Envía un mensaje y recibe eventos SSE del agente.
 * Usa fetch + ReadableStream (no EventSource, para poder hacer POST).
 */
export async function* streamChat(
  message: string,
  threadId?: string | null
): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      thread_id: threadId || undefined,
    }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status} ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || !trimmed.startsWith("data: ")) continue;
      const jsonStr = trimmed.slice(6); // Remove "data: "
      if (!jsonStr) continue;

      try {
        const event: ChatEvent = JSON.parse(jsonStr);
        yield event;
      } catch {
        console.warn("Failed to parse SSE event:", jsonStr);
      }
    }
  }

  // Process remaining buffer
  if (buffer.trim().startsWith("data: ")) {
    try {
      const event: ChatEvent = JSON.parse(buffer.trim().slice(6));
      yield event;
    } catch {
      // ignore
    }
  }
}

/** Obtiene el historial de un thread */
export async function getHistory(threadId: string) {
  const res = await fetch(`${API_BASE}/chat/history/${threadId}`);
  if (!res.ok) throw new Error(`History request failed: ${res.status}`);
  return res.json();
}

/** Borra el historial de un thread */
export async function deleteHistory(threadId: string) {
  const res = await fetch(`${API_BASE}/chat/history/${threadId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete request failed: ${res.status}`);
  return res.json();
}