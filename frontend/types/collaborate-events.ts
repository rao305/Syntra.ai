// Collaboration feature event types
// Phase abstraction for user-facing UI

export type AbstractPhase = "understand" | "research" | "reason_refine" | "crosscheck" | "synthesize";

// Map abstract phases to user-friendly labels
export const PHASE_LABELS: Record<AbstractPhase, string> = {
  understand: "Understanding your query",
  research: "Researching recent data",
  reason_refine: "Refining and organizing",
  crosscheck: "Cross-checking with other AI models",
  synthesize: "Synthesizing final report",
};

// Map internal roles to abstract phases
export const ROLE_TO_PHASE: Record<string, AbstractPhase> = {
  analyst: "understand",
  researcher: "research",
  creator: "reason_refine",
  critic: "reason_refine",
  internal_synthesizer: "reason_refine",
  council: "crosscheck",
  director: "synthesize",
};

export interface StanceCount {
  agree: number;
  disagree: number;
  mixed: number;
}

// Event types for SSE streaming
export interface PhaseStartEvent {
  type: "phase_start";
  phase: AbstractPhase;
  step_index: number; // 0-4 for 5 phases
  models?: string[];
}

export interface PhaseDeltaEvent {
  type: "phase_delta";
  phase: AbstractPhase;
  delta: string; // Incremental content
  model?: string;
  timestamp: number;
}

export interface PhaseEndEvent {
  type: "phase_end";
  phase: AbstractPhase;
  timestamp: number;
  latency_ms: number;
  tokens_used?: number;
  model?: string;
  council_summary?: StanceCount;
  model_info?: {
    provider: string;
    model: string;
    display_name: string;
  };
}

export interface FinalAnswerStartEvent {
  type: "final_answer_start";
  timestamp: number;
}

export interface FinalAnswerDeltaEvent {
  type: "final_answer_delta";
  delta: string;
  timestamp: number;
}

export interface FinalAnswerEndEvent {
  type: "final_answer_end";
  timestamp: number;
  confidence: "low" | "medium" | "high";
}

export interface StageStartEvent {
  type: "stage_start";
  role: string;
  label: string;
  model_display: string;
  step_index: number;
}

export interface StageEndEvent {
  type: "stage_end";
  role: string;
  latency_ms?: number;
}

export interface VisualizationEvent {
  type: "visualization";
  title: string;
  chart_data?: {
    type: string;
    url: string;
    metadata?: Record<string, any>;
  };
  image_data?: {
    url: string;
    alt_text: string;
  };
}

export type CollaborateEvent =
  | PhaseStartEvent
  | PhaseDeltaEvent
  | PhaseEndEvent
  | StageStartEvent
  | StageEndEvent
  | FinalAnswerStartEvent
  | FinalAnswerDeltaEvent
  | FinalAnswerEndEvent
  | VisualizationEvent;

// Helper functions
export function getRolePhase(role: string): AbstractPhase {
  return ROLE_TO_PHASE[role.toLowerCase()] || "understand";
}

export function getPhaseLabel(phase: AbstractPhase): string {
  return PHASE_LABELS[phase] || phase;
}

export function getPhaseIndex(phase: AbstractPhase): number {
  const phases: AbstractPhase[] = ["understand", "research", "reason_refine", "crosscheck", "synthesize"];
  return phases.indexOf(phase);
}

export function parseCollaborateEvent(eventText: string): CollaborateEvent | null {
  try {
    const lines = eventText.trim().split("\n");
    if (lines.length < 2) return null;

    // Parse SSE format: "event: type" followed by "data: {json}"
    const eventLine = lines[0].match(/^event:\s*(.+)$/);
    const dataLine = lines[1].match(/^data:\s*(.+)$/);

    if (!eventLine || !dataLine) return null;

    const eventType = eventLine[1].trim();
    const eventData = JSON.parse(dataLine[1].trim());

    return {
      type: eventType as any,
      ...eventData,
    };
  } catch (error) {
    console.error("Failed to parse collaborate event:", error);
    return null;
  }
}
