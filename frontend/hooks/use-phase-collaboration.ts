import { useState, useCallback } from "react";
import { CollaborateEvent, AbstractPhase, StanceCount } from "@/types/collaborate-events";

export interface Phase {
  phase: AbstractPhase;
  status: "pending" | "in_progress" | "completed";
  model?: string;
  provider?: string;
  latency_ms?: number;
  tokens_used?: number;
  council_summary?: StanceCount;
}

export interface UsePhaseCollaborationState {
  phases: Phase[];
  currentPhaseIndex: number;
  finalAnswerContent: string;
  finalAnswerDone: boolean;
  confidence?: "low" | "medium" | "high";
  isLoading: boolean;
  error?: string;
}

const defaultPhases: AbstractPhase[] = ["understand", "research", "reason_refine", "crosscheck", "synthesize"];

export function usePhaseCollaboration() {
  const [state, setState] = useState<UsePhaseCollaborationState>({
    phases: defaultPhases.map((phase) => ({
      phase,
      status: "pending",
    })),
    currentPhaseIndex: -1,
    finalAnswerContent: "",
    finalAnswerDone: false,
    isLoading: true,
  });

  const processEvent = useCallback((event: CollaborateEvent) => {
    setState((prevState) => {
      const newState = { ...prevState };

      switch (event.type) {
        case "phase_start": {
          const phaseIndex = defaultPhases.indexOf(event.phase);
          newState.currentPhaseIndex = phaseIndex;
          newState.phases = newState.phases.map((p, idx) => ({
            ...p,
            status: idx === phaseIndex ? ("in_progress" as const) : idx < phaseIndex ? ("completed" as const) : ("pending" as const),
          }));
          break;
        }

        case "phase_end": {
          const phaseIndex = defaultPhases.indexOf(event.phase);
          newState.phases[phaseIndex] = {
            ...newState.phases[phaseIndex],
            status: "completed",
            latency_ms: event.latency_ms,
            tokens_used: event.tokens_used,
            model: event.model_info?.display_name,
            provider: event.model_info?.provider,
            council_summary: event.council_summary,
          };
          break;
        }

        case "final_answer_start": {
          newState.isLoading = false;
          newState.finalAnswerContent = "";
          newState.finalAnswerDone = false;
          break;
        }

        case "final_answer_delta": {
          newState.finalAnswerContent += event.delta;
          break;
        }

        case "final_answer_end": {
          newState.finalAnswerDone = true;
          newState.confidence = event.confidence;
          newState.isLoading = false;
          break;
        }

        default:
          break;
      }

      return newState;
    });
  }, []);

  const reset = useCallback(() => {
    setState({
      phases: defaultPhases.map((phase) => ({
        phase,
        status: "pending",
      })),
      currentPhaseIndex: -1,
      finalAnswerContent: "",
      finalAnswerDone: false,
      isLoading: true,
    });
  }, []);

  const getPhases = useCallback(() => state.phases, [state.phases]);

  const getCurrentPhase = useCallback(() => {
    if (state.currentPhaseIndex >= 0) {
      return state.phases[state.currentPhaseIndex];
    }
    return null;
  }, [state.currentPhaseIndex, state.phases]);

  return {
    ...state,
    processEvent,
    reset,
    getPhases,
    getCurrentPhase,
  };
}
