import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types/chat";
import { MessageBubble } from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  onSuggestionClick?: (text: string) => void;
}

export function MessageList({ messages, onSuggestionClick }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list message-list--empty">
        <div className="empty-state">
          <h2>🔥 Hefesto</h2>
          <p>Asistente AI de PeopleTech — Inditex</p>
          <div className="empty-suggestions">
            <span className="suggestion" onClick={() => onSuggestionClick?.("¿Cuánto cuesta la electricidad de Endesa en España?")}>💡 ¿Cuánto cuesta la electricidad de Endesa en España?</span>
            <span className="suggestion" onClick={() => onSuggestionClick?.("Salarios de Zara en Italia")}>💰 Salarios de Zara en Italia</span>
            <span className="suggestion" onClick={() => onSuggestionClick?.("¿Qué dicen en LinkedIn sobre el CEO de Inditex?")}>📱 ¿Qué dicen en LinkedIn sobre el CEO de Inditex?</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={endRef} />
    </div>
  );
}