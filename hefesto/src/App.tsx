import { Flame, RotateCcw, X } from "lucide-react";
import { ChatInput } from "./components/ChatInput";
import { MessageList } from "./components/MessageList";
import { useChat } from "./hooks/useChat";

export default function App() {
  const { messages, isLoading, error, sendMessage, clearChat, dismissError } =
    useChat();

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="app-header-left">
          <Flame size={22} className="app-logo" />
          <h1>Hefesto</h1>
          <span className="app-badge">PeopleTech AI</span>
        </div>
        <div className="app-header-right">
          {messages.length > 0 && (
            <button className="btn-icon" onClick={clearChat} title="Nueva conversación">
              <RotateCcw size={16} />
            </button>
          )}
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button className="btn-icon" onClick={dismissError}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* Chat area */}
      <main className="app-main">
        <MessageList messages={messages} onSuggestionClick={sendMessage} />
      </main>

      {/* Input */}
      <footer className="app-footer">
        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </footer>
    </div>
  );
}