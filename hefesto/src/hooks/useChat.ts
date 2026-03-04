/**
 * Hook principal de chat — gestiona estado, streaming SSE y mensajes.
 */
import { useCallback, useRef, useState } from "react";
import { streamChat } from "../services/chatService";
import type {
  AssistantBlock,
  ChatEvent,
  ChatMessage,
  ChatState,
} from "../types/chat";

const initialState: ChatState = {
  messages: [],
  threadId: null,
  isLoading: false,
  error: null,
};

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function useChat() {
  const [state, setState] = useState<ChatState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || state.isLoading) return;

      // Add user message
      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        content: text.trim(),
        blocks: [],
        timestamp: Date.now(),
      };

      // Create assistant placeholder
      const assistantMsg: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: "",
        blocks: [],
        timestamp: Date.now(),
      };

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMsg, assistantMsg],
        isLoading: true,
        error: null,
      }));

      const assistantId = assistantMsg.id;

      try {
        for await (const event of streamChat(text, state.threadId)) {
          setState((prev) => {
            const msgs = [...prev.messages];
            const idx = msgs.findIndex((m) => m.id === assistantId);
            if (idx === -1) return prev;

            const msg = { ...msgs[idx], blocks: [...msgs[idx].blocks] };
            msgs[idx] = msg;

            return {
              ...prev,
              messages: msgs,
              ...processEvent(event, msg, prev.threadId),
            };
          });
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Error desconocido";
        setState((prev) => ({
          ...prev,
          error: errorMsg,
          isLoading: false,
        }));
      }
    },
    [state.isLoading, state.threadId]
  );

  const clearChat = useCallback(() => {
    setState(initialState);
  }, []);

  const dismissError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    messages: state.messages,
    threadId: state.threadId,
    isLoading: state.isLoading,
    error: state.error,
    sendMessage,
    clearChat,
    dismissError,
  };
}

/**
 * Procesa un evento SSE y actualiza el mensaje del asistente in-place.
 * Retorna campos parciales del estado a mergear.
 */
function processEvent(
  event: ChatEvent,
  msg: ChatMessage,
  currentThreadId: string | null
): Partial<ChatState> {
  switch (event.type) {
    case "thinking": {
      msg.blocks.push({ kind: "thinking", content: event.data });
      return {};
    }

    case "tool_start": {
      msg.blocks.push({
        kind: "tool",
        toolName: event.tool_name || "unknown",
        toolArgs: event.tool_args || {},
        status: "running",
      });
      return {};
    }

    case "tool_result": {
      // Find the last running tool block matching this tool
      for (let i = msg.blocks.length - 1; i >= 0; i--) {
        const b = msg.blocks[i];
        if (
          b.kind === "tool" &&
          b.status === "running" &&
          b.toolName === (event.tool_name || "unknown")
        ) {
          (b as AssistantBlock & { kind: "tool" }).result = event.data;
          (b as AssistantBlock & { kind: "tool" }).status = "done";
          break;
        }
      }
      return {};
    }

    case "text_delta": {
      // Append streaming token to last text block, or create one
      const lastBlock = msg.blocks[msg.blocks.length - 1];
      if (lastBlock && lastBlock.kind === "text") {
        lastBlock.content += event.data;
        msg.content = lastBlock.content;
      } else {
        msg.blocks.push({ kind: "text", content: event.data });
        msg.content = (msg.content || "") + event.data;
      }
      return {};
    }

    case "text": {
      // Final complete text — replaces any partial text_delta content
      const lastTextBlock = msg.blocks[msg.blocks.length - 1];
      if (lastTextBlock && lastTextBlock.kind === "text") {
        lastTextBlock.content = event.data;
      } else {
        msg.blocks.push({ kind: "text", content: event.data });
      }
      msg.content = event.data;
      return {};
    }

    case "done": {
      return {
        threadId: event.thread_id || currentThreadId,
        isLoading: false,
      };
    }

    case "error": {
      return {
        error: event.data,
        isLoading: false,
      };
    }

    default:
      return {};
  }
}