import { Send } from "lucide-react";
import { useRef, useState } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  };

  return (
    <div className="chat-input-container">
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Escribe tu consulta... Ej: ¿Cuánto paga Zara en España?"
          rows={1}
          disabled={disabled}
        />
        <button
          className="chat-send-btn"
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          title="Enviar mensaje"
        >
          <Send size={18} />
        </button>
      </div>
      <p className="chat-input-hint">
        Hefesto puede buscar precios de electricidad, salarios y menciones en
        redes sociales.
      </p>
    </div>
  );
}