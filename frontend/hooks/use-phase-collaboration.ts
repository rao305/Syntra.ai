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

export interface Stage {
  role: string;
  label: string;
  model_display: string;
  status: "pending" | "in_progress" | "completed";
  latency_ms?: number;
  loadingMessage: string;
}

export interface UsePhaseCollaborationState {
  phases: Phase[];
  currentPhaseIndex: number;
  stages: Stage[];
  currentStage?: Stage;
  finalAnswerContent: string;
  finalAnswerDone: boolean;
  confidence?: "low" | "medium" | "high";
  isLoading: boolean;
  error?: string;
}

const defaultPhases: AbstractPhase[] = ["understand", "research", "reason_refine", "crosscheck", "synthesize"];

// Stage loading messages for better UX
const STAGE_LOADING_MESSAGES: Record<string, string> = {
  analyst: "🤖 Analyzing your query...",
  researcher: "🔍 Researching recent data and trends...",
  creator: "✍️ Drafting the response...",
  critic: "💭 Refining and organizing...",
  internal_synth: "🧠 Synthesizing insights...",
  council: "👥 Getting external perspectives...",
  director: "🎯 Creating final detailed response...",
};

export function usePhaseCollaboration() {
  const [state, setState] = useState<UsePhaseCollaborationState>({
    phases: defaultPhases.map((phase) => ({
      phase,
      status: "pending",
    })),
    currentPhaseIndex: -1,
    stages: [],
    currentStage: undefined,
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

        case "stage_start": {
          const stage: Stage = {
            role: event.role,
            label: event.label,
            model_display: event.model_display,
            status: "in_progress",
            loadingMessage: STAGE_LOADING_MESSAGES[event.role] || `${event.label} processing...`,
          };
          newState.stages = [...newState.stages, stage];
          newState.currentStage = stage;
          break;
        }

        case "stage_end": {
          const stageIndex = newState.stages.findIndex((s) => s.role === event.role);
          if (stageIndex >= 0) {
            newState.stages[stageIndex] = {
              ...newState.stages[stageIndex],
              status: "completed",
              latency_ms: event.latency_ms,
            };
          }
          // Keep showing the last completed stage for context
          if (newState.currentStage?.role === event.role) {
            newState.currentStage = {
              ...newState.currentStage,
              status: "completed",
              latency_ms: event.latency_ms,
            };
          }
          break;
        }

        case "final_answer_start": {
          newState.isLoading = false;
          newState.finalAnswerContent = "";
          newState.finalAnswerDone = false;
          // Clear stages when final answer starts
          newState.stages = [];
          newState.currentStage = undefined;
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
      stages: [],
      currentStage: undefined,
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
