/**
 * Hook to manage thinking state during a collaborate run.
 *
 * Handles both detailed stage events and abstracted phase events:
 * - Initializing steps (5 phases or 7 stages)
 * - Processing events (phase_start/phase_end or stage_start/stage_end)
 * - Updating preview text
 * - Tracking council progress
 * - Collapse/expand state
 */

import { useCallback, useReducer } from "react";
import type {
  CollaborateEvent,
  StepRole,
  AbstractPhase,
  CouncilProgressEvent,
  TOTAL_STEPS,
  TOTAL_PHASES,
  PHASE_LABELS,
} from "@/types/collaborate-events";
import type { ThinkingStep, CouncilSummary } from "@/components/collaborate/ThinkingStrip";

export interface ThinkingState {
  steps: ThinkingStep[];
  currentIndex: number;
  councilSummary?: CouncilSummary;
  isCollapsed: boolean;
  error?: string;
}

type ThinkingAction =
  | { type: "INIT" }
  | { type: "INIT_PHASES" } // Initialize 5-phase view
  | {
      type: "STAGE_START";
      role: StepRole;
      label: string;
      modelDisplay: string;
      stepIndex: number;
    }
  | { type: "STAGE_DELTA"; role: StepRole; textDelta: string }
  | { type: "STAGE_END"; role: StepRole; latencyMs?: number }
  | {
      type: "PHASE_START";
      phase: AbstractPhase;
      label: string;
      modelDisplay: string;
      stepIndex: number;
    }
  | { type: "PHASE_DELTA"; phase: AbstractPhase; textDelta: string }
  | { type: "PHASE_END"; phase: AbstractPhase; latencyMs?: number }
  | {
      type: "COUNCIL_PROGRESS";
      completed: number;
      total: number;
      stanceCounts?: { agree: number; mixed: number; disagree: number };
    }
  | { type: "TOGGLE_COLLAPSED" }
  | { type: "SET_ERROR"; error: string }
  | { type: "RESET" };

const initialThinkingState: ThinkingState = {
  steps: [
    { role: "analyst", label: "Analyst", status: "pending", preview: "" },
    {
      role: "researcher",
      label: "Researcher",
      status: "pending",
      preview: "",
    },
    { role: "creator", label: "Creator", status: "pending", preview: "" },
    { role: "critic", label: "Critic", status: "pending", preview: "" },
    {
      role: "internal_synth",
      label: "Internal Report",
      status: "pending",
      preview: "",
    },
    {
      role: "council",
      label: "External Reviews",
      status: "pending",
      preview: "",
    },
    { role: "director", label: "Director", status: "pending", preview: "" },
  ],
  currentIndex: 0,
  isCollapsed: false,
};

const initialPhaseState: ThinkingState = {
  steps: [
    {
      phase: "understand",
      label: "Understanding your query",
      status: "pending",
      preview: "",
    },
    {
      phase: "research",
      label: "Researching recent data and trends",
      status: "pending",
      preview: "",
    },
    {
      phase: "reason_refine",
      label: "Refining and organizing the answer",
      status: "pending",
      preview: "",
    },
    {
      phase: "crosscheck",
      label: "Cross-checking with other AI models",
      status: "pending",
      preview: "",
    },
    {
      phase: "synthesize",
      label: "Synthesizing final report",
      status: "pending",
      preview: "",
    },
  ],
  currentIndex: 0,
  isCollapsed: false,
};

function thinkingReducer(
  state: ThinkingState,
  action: ThinkingAction
): ThinkingState {
  switch (action.type) {
    case "INIT":
      return initialThinkingState;

    case "INIT_PHASES":
      return initialPhaseState;

    case "STAGE_START": {
      const steps = [...state.steps];
      const stepIdx = action.stepIndex;

      if (stepIdx >= 0 && stepIdx < steps.length) {
        steps[stepIdx] = {
          ...steps[stepIdx],
          role: action.role,
          label: action.label,
          modelDisplay: action.modelDisplay,
          status: "active",
          preview: "",
        };
      }

      return {
        ...state,
        steps,
        currentIndex: stepIdx,
      };
    }

    case "STAGE_DELTA": {
      const steps = [...state.steps];
      const stepIdx = steps.findIndex((s) => s.role === action.role);

      if (stepIdx >= 0) {
        const currentPreview = steps[stepIdx].preview;
        // Keep last 300 chars + new delta
        const combined = currentPreview + action.textDelta;
        steps[stepIdx] = {
          ...steps[stepIdx],
          preview: combined.slice(-300),
        };
      }

      return { ...state, steps };
    }

    case "STAGE_END": {
      const steps = [...state.steps];
      const stepIdx = steps.findIndex((s) => s.role === action.role);

      if (stepIdx >= 0) {
        steps[stepIdx] = {
          ...steps[stepIdx],
          status: "done",
          latency_ms: action.latencyMs,
        };
      }

      return { ...state, steps };
    }

    case "PHASE_START": {
      const steps = [...state.steps];
      const stepIdx = action.stepIndex;

      if (stepIdx >= 0 && stepIdx < steps.length) {
        steps[stepIdx] = {
          ...steps[stepIdx],
          phase: action.phase,
          label: action.label,
          modelDisplay: action.modelDisplay,
          status: "active",
          preview: "",
        };
      }

      return {
        ...state,
        steps,
        currentIndex: stepIdx,
      };
    }

    case "PHASE_DELTA": {
      const steps = [...state.steps];
      const stepIdx = steps.findIndex((s) => s.phase === action.phase);

      if (stepIdx >= 0) {
        const currentPreview = steps[stepIdx].preview;
        // Keep last 300 chars + new delta
        const combined = currentPreview + action.textDelta;
        steps[stepIdx] = {
          ...steps[stepIdx],
          preview: combined.slice(-300),
        };
      }

      return { ...state, steps };
    }

    case "PHASE_END": {
      const steps = [...state.steps];
      const stepIdx = steps.findIndex((s) => s.phase === action.phase);

      if (stepIdx >= 0) {
        steps[stepIdx] = {
          ...steps[stepIdx],
          status: "done",
          latency_ms: action.latencyMs,
        };
      }

      return { ...state, steps };
    }

    case "COUNCIL_PROGRESS": {
      return {
        ...state,
        councilSummary: {
          completed: action.completed,
          total: action.total,
          stanceCounts: action.stanceCounts,
        },
      };
    }

    case "TOGGLE_COLLAPSED":
      return { ...state, isCollapsed: !state.isCollapsed };

    case "SET_ERROR":
      return { ...state, error: action.error };

    case "RESET":
      return initialThinkingState;

    default:
      return state;
  }
}

export function useThinkingState() {
  const [state, dispatch] = useReducer(thinkingReducer, initialThinkingState);

  const init = useCallback(() => {
    dispatch({ type: "INIT" });
  }, []);

  const handleEvent = useCallback((event: CollaborateEvent) => {
    switch (event.type) {
      // Detailed stage events (for internal logging, not displayed by default)
      case "stage_start":
        dispatch({
          type: "STAGE_START",
          role: event.role,
          label: event.label,
          modelDisplay: event.model_display,
          stepIndex: event.step_index,
        });
        break;

      case "stage_delta":
        dispatch({
          type: "STAGE_DELTA",
          role: event.role,
          textDelta: event.text_delta,
        });
        break;

      case "stage_end":
        dispatch({
          type: "STAGE_END",
          role: event.role,
          latencyMs: event.latency_ms,
        });
        break;

      // Abstracted phase events (displayed in UI)
      case "phase_start":
        // Auto-switch to phase view on first phase event
        dispatch({
          type: "PHASE_START",
          phase: event.phase,
          label: event.label,
          modelDisplay: event.model_display,
          stepIndex: event.step_index,
        });
        break;

      case "phase_delta":
        dispatch({
          type: "PHASE_DELTA",
          phase: event.phase,
          textDelta: event.text_delta,
        });
        break;

      case "phase_end":
        dispatch({
          type: "PHASE_END",
          phase: event.phase,
          latencyMs: event.latency_ms,
        });
        break;

      case "council_progress":
        dispatch({
          type: "COUNCIL_PROGRESS",
          completed: event.completed,
          total: event.total,
          stanceCounts: event.stance_counts,
        });
        break;

      case "error":
        dispatch({
          type: "SET_ERROR",
          error: event.message,
        });
        break;

      default:
        break;
    }
  }, []);

  const toggleCollapsed = useCallback(() => {
    dispatch({ type: "TOGGLE_COLLAPSED" });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: "RESET" });
  }, []);

  return {
    ...state,
    init,
    handleEvent,
    toggleCollapsed,
    reset,
  };
}

/**
 * Alternative hook for async event streaming (if you're using EventSource / fetch)
 */
export function useCollaborateStreaming(
  threadId: string,
  message: string,
  onComplete?: (response: any) => void
) {
  const thinking = useThinkingState();
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [finalAnswer, setFinalAnswer] = React.useState("");

  const startStream = React.useCallback(async () => {
    thinking.init();
    setIsStreaming(true);

    try {
      const response = await fetch(
        `/api/threads/${threadId}/collaborate-stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, mode: "auto" }),
        }
      );

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let finalAnswerText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const eventStr = line.slice(6);
            const event = JSON.parse(eventStr);

            if (event.type === "final_answer_delta") {
              finalAnswerText += event.text_delta;
              setFinalAnswer(finalAnswerText);
            } else if (event.type === "final_answer_done") {
              onComplete?.(event.response);
            } else {
              thinking.handleEvent(event);
            }
          }
        }
      }
    } catch (err) {
      thinking.dispatch({
        type: "SET_ERROR",
        error: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setIsStreaming(false);
    }
  }, [threadId, message, thinking, onComplete]);

  return {
    ...thinking,
    isStreaming,
    finalAnswer,
    startStream,
  };
}

// Re-export for convenience
import * as React from "react";
