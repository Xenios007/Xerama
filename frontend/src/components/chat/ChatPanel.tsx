import { useEffect, useRef, useState } from "react";
import { Button } from "../ui/Button";
import { API_BASE_URL } from "../../api/client";
import { useChatStatus } from "../../api/queries";
import "./ChatPanel.css";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

function wsUrl(path: string): string {
  return `${API_BASE_URL.replace(/^http/, "ws")}${path}`;
}

/**
 * Xerama Assistant - a global chat drawer backed by OpenRouter chat
 * completions (see src/xerama/api/routers/chat.py) - not the Claude Agent
 * SDK, since that requires a separate Anthropic key and disallows riding a
 * personal claude.ai login for a third-party product. Defaults to a Claude
 * model billed through OpenRouter instead.
 */
export function ChatPanel() {
  const status = useChatStatus();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!open || !status.data?.configured || socketRef.current) return;

    const socket = new WebSocket(wsUrl("/chat/ws"));
    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => {
      setConnected(false);
      socketRef.current = null;
    };
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as { type: string; text?: string };
      if (payload.type === "text" && payload.text) {
        const chunk = payload.text;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant") {
            return [...prev.slice(0, -1), { role: "assistant", text: last.text + chunk }];
          }
          return [...prev, { role: "assistant", text: chunk }];
        });
      } else if (payload.type === "turn_complete") {
        setBusy(false);
      }
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [open, status.data?.configured]);

  function send() {
    const text = draft.trim();
    const socket = socketRef.current;
    if (!text || !socket || socket.readyState !== WebSocket.OPEN) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    socket.send(JSON.stringify({ type: "message", text }));
    setDraft("");
    setBusy(true);
  }

  function interrupt() {
    socketRef.current?.send(JSON.stringify({ type: "interrupt" }));
    setBusy(false);
  }

  return (
    <>
      <button
        className="xr-chat__toggle"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close assistant" : "Open assistant"}
      >
        {open ? "×" : "Assistant"}
      </button>

      {open && (
        <div className="xr-chat__panel">
          <div className="xr-chat__header">
            <strong>Xerama Assistant</strong>
            <span className="xr-chat__subtitle">
              {status.data?.model ? `via OpenRouter · ${status.data.model}` : "via OpenRouter"}
            </span>
          </div>

          {status.isLoading ? (
            <p className="xr-chat__empty">Loading…</p>
          ) : !status.data?.configured ? (
            <p className="xr-chat__empty">
              Add an OpenRouter API key (<code>OPENROUTER_API_KEY</code>) to enable the assistant.
            </p>
          ) : (
            <>
              <div className="xr-chat__messages">
                {messages.length === 0 && (
                  <p className="xr-chat__empty">
                    Ask for help with a story concept, a shot prompt, or creative direction.
                  </p>
                )}
                {messages.map((m, i) => (
                  <div key={i} className={`xr-chat__message xr-chat__message--${m.role}`}>
                    {m.text}
                  </div>
                ))}
                {!connected && <p className="xr-chat__empty">Connecting…</p>}
              </div>
              <div className="xr-chat__input-row">
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && send()}
                  placeholder="Ask the assistant…"
                  aria-label="Message the assistant"
                  disabled={!connected}
                />
                {busy ? (
                  <Button variant="danger" onClick={interrupt}>
                    Stop
                  </Button>
                ) : (
                  <Button onClick={send} disabled={!connected || !draft.trim()}>
                    Send
                  </Button>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
