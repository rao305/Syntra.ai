/**
 * Example: Chat component with integrated Collaborate thinking UI
 *
 * This shows how to wire ThinkingStrip into your existing chat component.
 * Adapt this pattern to your actual chat layout.
 */

import { useState, useRef, useEffect } from "react";
import { ThinkingStrip } from "@/components/collaborate/ThinkingStrip";
import { useThinkingState } from "@/hooks/useThinkingState";
import {
  parseCollaborateEvent,
  type CollaborateEvent,
} from "@/types/collaborate-events";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinkingState?: any; // Can store the full thinking state for later inspection
}

/**
 * Example Chat Component
 *
 * Usage:
 * <ChatWithThinking threadId="thread-123" />
 */
export function ChatWithThinking({ threadId }: { threadId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Thinking state management
  const thinking = useThinkingState();
  const [isThinkingCollapsed, setIsThinkingCollapsed] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  /**
   * Handle collaborate request with streaming
   */
  async function handleCollaborate() {
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: inputValue,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    // Initialize thinking state
    thinking.init();

    try {
      // Call streaming endpoint
      const response = await fetch(
        `/api/threads/${threadId}/collaborate-stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: inputValue,
            mode: "auto",
          }),
        }
      );

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let assistantContent = "";
      let collaborateResponse: any = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const eventStr = line.slice(6).trim();
            if (!eventStr) continue;

            const event = parseCollaborateEvent(eventStr);
            if (!event) continue;

            // Handle different event types
            if (event.type === "final_answer_delta") {
              assistantContent += event.text_delta;
            } else if (event.type === "final_answer_done") {
              collaborateResponse = event.response;
              // Auto-collapse thinking after complete
              setIsThinkingCollapsed(true);
            } else {
              // All other events update thinking state
              thinking.handleEvent(event);
            }
          }
        }
      }

      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: assistantContent,
        thinkingState: collaborateResponse,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Collaborate error:", err);
      const errorMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-50">
      {/* Header */}
      <div className="border-b border-slate-700 px-4 py-3">
        <h1 className="text-lg font-semibold">Chat with Collaborate</h1>
        <p className="text-xs text-slate-400">
          Thread: {threadId}
        </p>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className="space-y-2">
            {/* User message */}
            {msg.role === "user" && (
              <div className="flex justify-end">
                <div className="max-w-2xl rounded-lg bg-indigo-600/70 px-4 py-2 text-sm">
                  {msg.content}
                </div>
              </div>
            )}

            {/* Assistant message */}
            {msg.role === "assistant" && (
              <div className="space-y-2">
                {/* Thinking strip (while loading or if thinking state exists) */}
                {(isLoading || msg.thinkingState) && (
                  <ThinkingStrip
                    steps={thinking.steps}
                    currentIndex={thinking.currentIndex}
                    councilSummary={thinking.councilSummary}
                    isCollapsed={isThinkingCollapsed}
                    onToggleCollapsed={() =>
                      setIsThinkingCollapsed(!isThinkingCollapsed)
                    }
                  />
                )}

                {/* Final answer */}
                <div className="max-w-2xl rounded-lg bg-slate-900/50 px-4 py-3 border border-slate-700">
                  <p className="text-sm leading-relaxed text-slate-200">
                    {msg.content}
                  </p>

                  {/* Confidence badge (if available) */}
                  {msg.thinkingState?.final_answer?.explanation && (
                    <div className="mt-3 flex items-center gap-2 text-xs">
                      <span className="text-slate-400">Confidence:</span>
                      <span
                        className={[
                          "rounded-full px-2 py-1",
                          msg.thinkingState.final_answer.explanation
                            .confidence_level === "high"
                            ? "bg-emerald-900/50 text-emerald-300"
                            : "bg-amber-900/50 text-amber-300",
                        ].join(" ")}
                      >
                        {msg.thinkingState.final_answer.explanation.confidence_level}
                      </span>
                    </div>
                  )}

                  {/* Optional: "View detailed reasoning" button */}
                  {msg.thinkingState && (
                    <button className="mt-2 text-xs text-indigo-400 hover:text-indigo-300">
                      View detailed reasoning →
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && thinking.steps.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <div className="h-2 w-2 rounded-full bg-slate-500 animate-pulse" />
            Starting collaboration...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-slate-700 px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleCollaborate();
              }
            }}
            placeholder="Ask a question... (shift+enter for new line)"
            className="flex-1 rounded-lg bg-slate-900 px-4 py-2 text-sm text-slate-50 placeholder-slate-500 border border-slate-700 focus:border-indigo-500 focus:outline-none"
            disabled={isLoading}
          />
          <button
            onClick={handleCollaborate}
            disabled={isLoading || !inputValue.trim()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Collaborating..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatWithThinking;
