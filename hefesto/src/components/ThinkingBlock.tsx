import { Brain, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

interface Props {
  content: string;
}

export function ThinkingBlock({ content }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="thinking-block" onClick={() => setExpanded(!expanded)}>
      <div className="thinking-header">
        <Brain size={14} />
        <span>Razonando...</span>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </div>
      {expanded && <div className="thinking-content">{content}</div>}
    </div>
  );
}