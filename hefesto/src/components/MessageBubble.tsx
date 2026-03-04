import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User } from "lucide-react";
import type { ChatMessage } from "../types/chat";
import { ThinkingBlock } from "./ThinkingBlock";
import { ToolBlock } from "./ToolBlock";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  if (message.role === "user") {
    return (
      <div className="message message--user">
        <div className="message-avatar">
          <User size={16} />
        </div>
        <div className="message-body">
          <p>{message.content}</p>
        </div>
      </div>
    );
  }

  // Assistant message — render blocks
  return (
    <div className="message message--assistant">
      <div className="message-avatar message-avatar--bot">
        <Bot size={16} />
      </div>
      <div className="message-body">
        {message.blocks.length === 0 && (
          <div className="message-loading">
            <span className="dot-pulse" />
          </div>
        )}
        {message.blocks.map((block, i) => {
          switch (block.kind) {
            case "thinking":
              return <ThinkingBlock key={i} content={block.content} />;
            case "tool":
              return <ToolBlock key={i} block={block} />;
            case "text":
              return (
                <div key={i} className="message-text">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {block.content}
                  </ReactMarkdown>
                </div>
              );
            default:
              return null;
          }
        })}
      </div>
    </div>
  );
}