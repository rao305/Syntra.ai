"use client";

import { useEffect, useRef, useState } from "react";
import { ThinkingStrip } from "./collaborate/ThinkingStrip";
import { FinalAnswerCard } from "./collaborate/FinalAnswerCard";
import { SelectionExplanation } from "./collaborate/SelectionExplanation";
import { DetailedAnalysisPanel } from "./collaborate/DetailedAnalysisPanel";
import { usePhaseCollaboration } from "@/hooks/use-phase-collaboration";
import { parseCollaborateEvent } from "@/types/collaborate-events";
import { CollaborateResponse } from "@/lib/collaborate-types";

interface CollaborationIntegrationProps {
  threadId: string;
  prompt: string;
  onComplete?: (response: CollaborateResponse) => void;
}

type ErrorType = "network" | "timeout" | "api" | "parsing" | "unknown";

interface ErrorState {
  type: ErrorType;
  message: string;
  details?: string;
}

export function CollaborationIntegration({ threadId, prompt, onComplete }: CollaborationIntegrationProps) {
  const { processEvent, reset: resetPhaseState, ...phaseState } = usePhaseCollaboration();
  const [collaborateResponse, setCollaborateResponse] = useState<CollaborateResponse | null>(null);
  const [error, setError] = useState<ErrorState | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const classifyError = (err: unknown): ErrorState => {
    if (err instanceof TypeError && err.message.includes("fetch")) {
      return {
        type: "network",
        message: "Network connection failed",
        details: "Unable to reach the server. Please check your internet connection.",
      };
    }

    if (err instanceof Error) {
      if (err.message.includes("timeout") || err.name === "AbortError") {
        return {
          type: "timeout",
          message: "Request timeout",
          details: "The collaboration took too long. Please try again.",
        };
      }

      if (err.message.includes("HTTP")) {
        const match = err.message.match(/HTTP (\d+)/);
        const statusCode = match ? parseInt(match[1]) : 500;
        if (statusCode === 401) {
          return {
            type: "api",
            message: "Authentication failed",
            details: "Please log in again and try again.",
          };
        }
        if (statusCode === 429) {
          return {
            type: "api",
            message: "Rate limit exceeded",
            details: "Too many requests. Please wait a moment and try again.",
          };
        }
        if (statusCode >= 500) {
          return {
            type: "api",
            message: "Server error",
            details: "The server encountered an error. Please try again later.",
          };
        }
        return {
          type: "api",
          message: "API error",
          details: err.message,
        };
      }

      if (err.message.includes("parse")) {
        return {
          type: "parsing",
          message: "Data parsing error",
          details: "Failed to parse server response. This may be a temporary issue.",
        };
      }
    }

    return {
      type: "unknown",
      message: "Unknown error occurred",
      details: err instanceof Error ? err.message : String(err),
    };
  };

  const handleRetry = () => {
    setIsRetrying(true);
    setError(null);
    setCollaborateResponse(null);
    resetPhaseState();
    setRetryCount((prev) => prev + 1);
  };

  useEffect(() => {
    if (!threadId || !prompt) return;

    // Start collaboration streaming
    const startCollaboration = async () => {
      try {
        setError(null);
        abortControllerRef.current = new AbortController();
        const timeoutId = setTimeout(() => abortControllerRef.current?.abort(), 120000); // 2 minute timeout

        // Construct API request
        const response = await fetch(`/api/threads/${threadId}/collaborate-stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-org-id": "org_demo", // This should come from auth context in production
          },
          body: JSON.stringify({
            message: prompt,
            mode: "auto",
          }),
          signal: abortControllerRef.current.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorBody = await response.text();
          throw new Error(
            `HTTP ${response.status}: ${response.statusText}. ${errorBody ? errorBody.substring(0, 100) : ""}`
          );
        }

        if (!response.body) {
          throw new Error("No response body");
        }

        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let eventCount = 0;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");

          // Process complete lines, keep incomplete line in buffer
          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            // Parse SSE format
            if (line.startsWith("event:")) {
              const eventType = line.substring("event:".length).trim();
              const nextLine = lines[i + 1];

              if (nextLine && nextLine.startsWith("data:")) {
                const dataStr = nextLine.substring("data:".length).trim();
                try {
                  const eventData = JSON.parse(dataStr);
                  const event = {
                    type: eventType,
                    ...eventData,
                  };

                  // Process event
                  processEvent(event);
                  eventCount++;

                  // If this is final_answer_end, save the response
                  if (eventType === "final_answer_end" && eventData.full_response) {
                    setCollaborateResponse(eventData.full_response);
                    onComplete?.(eventData.full_response);
                  }
                } catch (e) {
                  console.warn("Failed to parse event data:", dataStr, e);
                  throw new Error(
                    `Failed to parse event: ${e instanceof Error ? e.message : String(e)}`
                  );
                }
              }
            }
          }

          // Keep the incomplete line for next iteration
          buffer = lines[lines.length - 1];
        }

        // Verify we got events
        if (eventCount === 0) {
          throw new Error("No events received from server");
        }
      } catch (err) {
        const errorState = classifyError(err);
        setError(errorState);
        console.error("Collaboration error:", err);
      } finally {
        setIsRetrying(false);
      }
    };

    startCollaboration();

    // Cleanup
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [threadId, prompt, processEvent, onComplete, isRetrying]);

  const getErrorIcon = (type: ErrorType) => {
    switch (type) {
      case "network":
        return "🌐";
      case "timeout":
        return "⏱️";
      case "api":
        return "🔌";
      case "parsing":
        return "📄";
      default:
        return "⚠️";
    }
  };

  const getErrorRecoveryActions = (type: ErrorType) => {
    switch (type) {
      case "network":
        return [
          "Check your internet connection",
          "Try again in a moment",
          "If problem persists, try another network",
        ];
      case "timeout":
        return [
          "Increase your patience (collaboration can take 1-2 minutes)",
          "Check if server is responding",
          "Try a shorter or simpler prompt",
        ];
      case "api":
        return ["Verify your API keys are configured", "Check server status", "Contact support if error persists"];
      case "parsing":
        return ["This is a temporary issue, please retry", "Check server logs for details"];
      default:
        return ["Try again", "Check the console for more details"];
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Error Display with Recovery UI */}
      {error && (
        <div className="w-full bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <span className="text-3xl flex-shrink-0">{getErrorIcon(error.type)}</span>
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-red-900 dark:text-red-200 text-lg">{error.message}</h4>
              <p className="text-sm text-red-800 dark:text-red-300 mt-1">{error.details}</p>

              {/* Recovery suggestions */}
              {retryCount < 3 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold text-red-900 dark:text-red-200 mb-2">What you can do:</p>
                  <ul className="space-y-1">
                    {getErrorRecoveryActions(error.type).map((action, idx) => (
                      <li key={idx} className="text-xs text-red-800 dark:text-red-300 flex items-start gap-2">
                        <span className="text-red-600 dark:text-red-400 mt-0.5">→</span>
                        <span>{action}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Action buttons */}
              <div className="mt-4 flex flex-wrap gap-2">
                {retryCount < 3 && (
                  <button
                    onClick={handleRetry}
                    disabled={isRetrying}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    {isRetrying ? "Retrying..." : `Retry (${retryCount + 1}/3)`}
                  </button>
                )}
                <button
                  onClick={() => {
                    setError(null);
                    setRetryCount(0);
                  }}
                  className="px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-50 text-sm font-medium rounded-lg transition-colors"
                >
                  Dismiss
                </button>
              </div>

              {/* Max retries reached */}
              {retryCount >= 3 && (
                <div className="mt-4 p-3 bg-red-100 dark:bg-red-900/30 rounded border border-red-200 dark:border-red-800">
                  <p className="text-xs text-red-900 dark:text-red-200">
                    Maximum retries reached. Please check the error details above or contact support.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Thinking Strip - Progress Indicator */}
      <ThinkingStrip isVisible={!phaseState.finalAnswerDone && phaseState.isLoading} />

      {/* Final Answer - Only show when done */}
      {collaborateResponse && (
        <div className="space-y-6">
          <FinalAnswerCard finalAnswer={collaborateResponse.final_answer} meta={collaborateResponse.meta} />

          {/* How This Answer Was Selected */}
          <SelectionExplanation data={collaborateResponse} />

          {/* Summary Stats */}
          <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground bg-muted/30 rounded-lg p-3 flex-wrap">
            <div className="flex items-center gap-1">
              <span className="font-medium">📊 Models:</span>
              <span>{collaborateResponse.meta.models_used.length}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-medium">👥 Reviews:</span>
              <span>{collaborateResponse.meta.num_external_reviews}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-medium">⏱️ Time:</span>
              <span>{(collaborateResponse.meta.total_latency_ms / 1000).toFixed(1)}s</span>
            </div>
          </div>

          {/* Optional: Collapsible detailed analysis */}
          <details className="group rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50 p-6 shadow-sm">
            <summary className="flex cursor-pointer items-center justify-between text-sm font-semibold list-none select-none">
              <span className="flex items-center gap-3">
                <span className="text-xl">🔍</span>
                <span className="text-slate-900 dark:text-slate-50">View Detailed Analysis</span>
                <span className="text-xs font-normal text-slate-600 dark:text-slate-400">
                  (Pipeline stages, expert reviews, metadata)
                </span>
              </span>
              <svg
                className="w-5 h-5 transition-transform group-open:rotate-180 flex-shrink-0 text-slate-600 dark:text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </summary>
            <div className="mt-6 border-t border-slate-200 pt-6 dark:border-slate-700">
              <DetailedAnalysisPanel data={collaborateResponse} />
            </div>
          </details>
        </div>
      )}

      {/* Loading State */}
      {phaseState.isLoading && !collaborateResponse && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin inline-block h-8 w-8 text-blue-600 dark:text-blue-400 mb-3">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="text-slate-600 dark:text-slate-400">Processing collaboration...</p>
          </div>
        </div>
      )}
    </div>
  );
}
