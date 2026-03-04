/** Tipos de evento SSE que emite el backend */
export type EventType =
  | "thinking"
  | "tool_start"
  | "tool_result"
  | "text_delta"
  | "text"
  | "done"
  | "error";

/** Evento SSE individual del ChatTeamsAgent */
export interface ChatEvent {
  type: EventType;
  data: string;
  timestamp: number;
  tool_name?: string;
  tool_args?: Record<string, string>;
  thread_id?: string;
}

/** Tipos de mensaje en la UI */
export type MessageRole = "user" | "assistant" | "tool";

/** Bloque dentro de un mensaje del asistente */
export interface ThinkingBlock {
  kind: "thinking";
  content: string;
}

export interface ToolBlock {
  kind: "tool";
  toolName: string;
  toolArgs: Record<string, string>;
  result?: string;
  status: "running" | "done" | "error";
}

export interface TextBlock {
  kind: "text";
  content: string;
}

export type AssistantBlock = ThinkingBlock | ToolBlock | TextBlock;

/** Mensaje en el chat */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string; // Para user messages
  blocks: AssistantBlock[]; // Para assistant messages
  timestamp: number;
}

/** Estado global del chat */
export interface ChatState {
  messages: ChatMessage[];
  threadId: string | null;
  isLoading: boolean;
  error: string | null;
}