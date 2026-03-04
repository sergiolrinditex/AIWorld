import {
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Loader2,
  Wrench,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import type { ToolBlock as ToolBlockType } from "../types/chat";

interface Props {
  block: ToolBlockType;
}

const statusIcons = {
  running: <Loader2 size={14} className="spin" />,
  done: <CheckCircle size={14} className="text-success" />,
  error: <XCircle size={14} className="text-error" />,
};

export function ToolBlock({ block }: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasArgs = Object.keys(block.toolArgs).length > 0;
  const hasResult = !!block.result;

  return (
    <div className={`tool-block tool-block--${block.status}`}>
      <div className="tool-header" onClick={() => setExpanded(!expanded)}>
        <Wrench size={14} />
        <span className="tool-name">{block.toolName}</span>
        {statusIcons[block.status]}
        {(hasArgs || hasResult) &&
          (expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />)}
      </div>

      {expanded && (
        <div className="tool-details">
          {hasArgs && (
            <div className="tool-args">
              <strong>Parámetros:</strong>
              <pre>{JSON.stringify(block.toolArgs, null, 2)}</pre>
            </div>
          )}
          {hasResult && (
            <div className="tool-result">
              <strong>Resultado:</strong>
              <pre>{block.result}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}