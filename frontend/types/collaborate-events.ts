/**
 * Streaming event types for Collaborate pipeline.
 *
 * These events are emitted by the backend as the pipeline progresses,
 * allowing the frontend to animate the thinking UI in real-time.
 */

export type StepRole =
  | "analyst"
  | "researcher"
  | "creator"
  | "critic"
  | "internal_synth"
  | "council"
  | "director";

/**
 * User-facing abstract phases that group internal roles
 * These provide a cleaner, simpler view of the collaboration process
 */
export type AbstractPhase =
  | "understand"
  | "research"
  | "reason_refine"
  | "crosscheck"
  | "synthesize";

export type CollaborateEventType =
  | "stage_start"
  | "stage_delta"
  | "stage_end"
  | "council_progress"
  | "final_answer_delta"
  | "final_answer_done"
  | "error"
  | "phase_start"
  | "phase_delta"
  | "phase_end";

// ===== Base Event =====

export interface BaseCollaborateEvent {
  type: CollaborateEventType;
  run_id: string;
  timestamp: string;
}

// ===== Stage Events =====

export interface StageStartEvent extends BaseCollaborateEvent {
  type: "stage_start";
  role: StepRole;
  label: string; // e.g. "Analyst", "Researcher"
  model_display: string; // e.g. "Gemini 2.0 Pro"
  step_index: number; // 0–6 for "Step X of 7"
}

export interface StageDeltaEvent extends BaseCollaborateEvent {
  type: "stage_delta";
  role: StepRole;
  text_delta: string; // small snippet for the scrolling preview
}

export interface StageEndEvent extends BaseCollaborateEvent {
  type: "stage_end";
  role: StepRole;
  latency_ms?: number;
}

// ===== Council Events =====

export interface CouncilProgressEvent extends BaseCollaborateEvent {
  type: "council_progress";
  completed: number; // e.g. 3 reviewers done
  total: number; // e.g. 5 total reviewers
  stance_counts?: {
    agree: number;
    mixed: number;
    disagree: number;
  };
}

// ===== Final Answer Events =====

export interface FinalAnswerDeltaEvent extends BaseCollaborateEvent {
  type: "final_answer_delta";
  text_delta: string;
}

export interface FinalAnswerDoneEvent extends BaseCollaborateEvent {
  type: "final_answer_done";
  // Full response object attached when streaming completes
  response: any; // Type as CollaborateResponse if importing
}

// ===== Error Event =====

export interface ErrorEvent extends BaseCollaborateEvent {
  type: "error";
  stage?: StepRole;
  message: string;
  error_code?: string;
}

// ===== Abstracted Phase Events (for user-facing UI) =====

/**
 * Signals the start of an abstract phase.
 * This groups one or more internal stage roles into a user-facing phase.
 */
export interface PhaseStartEvent extends BaseCollaborateEvent {
  type: "phase_start";
  phase: AbstractPhase;
  label: string; // e.g. "Understanding your query"
  model_display: string; // e.g. "GPT-4.1" or "Perplexity, Gemini, GPT, Kimi, OpenRouter"
  step_index: number; // 0–4 for "Step X of 5"
}

/**
 * Preview/delta text for an abstract phase
 */
export interface PhaseDeltaEvent extends BaseCollaborateEvent {
  type: "phase_delta";
  phase: AbstractPhase;
  text_delta: string; // snippet for preview
}

/**
 * Signals the completion of an abstract phase
 */
export interface PhaseEndEvent extends BaseCollaborateEvent {
  type: "phase_end";
  phase: AbstractPhase;
  latency_ms?: number;
}

// ===== Union Type =====

export type CollaborateEvent =
  | StageStartEvent
  | StageDeltaEvent
  | StageEndEvent
  | CouncilProgressEvent
  | FinalAnswerDeltaEvent
  | FinalAnswerDoneEvent
  | ErrorEvent
  | PhaseStartEvent
  | PhaseDeltaEvent
  | PhaseEndEvent;

// ===== Helper function to parse events =====

export function parseCollaborateEvent(json: string): CollaborateEvent | null {
  try {
    const data = JSON.parse(json);
    if (!data.type) return null;

    // Basic validation
    if (
      [
        "stage_start",
        "stage_delta",
        "stage_end",
        "council_progress",
        "final_answer_delta",
        "final_answer_done",
        "error",
        "phase_start",
        "phase_delta",
        "phase_end",
      ].includes(data.type)
    ) {
      return data;
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Helper to extract role from event (works for most event types)
 */
export function getRoleFromEvent(event: CollaborateEvent): StepRole | null {
  if (
    event.type === "stage_start" ||
    event.type === "stage_delta" ||
    event.type === "stage_end"
  ) {
    return event.role;
  }
  return null;
}

/**
 * Helper to get human-readable label for a role
 */
export const ROLE_LABELS: Record<StepRole, string> = {
  analyst: "Analyst",
  researcher: "Researcher",
  creator: "Creator",
  critic: "Critic",
  internal_synth: "Internal Report",
  council: "External Reviews",
  director: "Director",
};

/**
 * Step index for each role (for "Step X of 7" display)
 */
export const ROLE_INDICES: Record<StepRole, number> = {
  analyst: 0,
  researcher: 1,
  creator: 2,
  critic: 3,
  internal_synth: 4,
  council: 5,
  director: 6,
};

export const TOTAL_STEPS = 7;

// ===== Abstract Phase Mappings (User-facing) =====

/**
 * Map internal roles to user-facing abstract phases
 */
export const ROLE_TO_PHASE: Record<StepRole, AbstractPhase> = {
  analyst: "understand",
  creator: "understand",
  researcher: "research",
  critic: "reason_refine",
  internal_synth: "reason_refine",
  council: "crosscheck",
  director: "synthesize",
};

/**
 * Map abstract phases to display labels for the thinking UI
 */
export const PHASE_LABELS: Record<AbstractPhase, string> = {
  understand: "Understanding your query",
  research: "Researching recent data and trends",
  reason_refine: "Refining and organizing the answer",
  crosscheck: "Cross-checking with other AI models",
  synthesize: "Synthesizing final report",
};

/**
 * Phase indices for "Step X of 5" display
 */
export const PHASE_INDICES: Record<AbstractPhase, number> = {
  understand: 0,
  research: 1,
  reason_refine: 2,
  crosscheck: 3,
  synthesize: 4,
};

export const TOTAL_PHASES = 5;

/**
 * Get the abstract phase for a given internal role
 */
export function getRolePhase(role: StepRole): AbstractPhase {
  return ROLE_TO_PHASE[role];
}

/**
 * Get the display label for a phase
 */
export function getPhaseLabel(phase: AbstractPhase): string {
  return PHASE_LABELS[phase];
}

/**
 * Get the phase from a phase event
 */
export function getPhaseFromEvent(
  event: CollaborateEvent
): AbstractPhase | null {
  if (
    event.type === "phase_start" ||
    event.type === "phase_delta" ||
    event.type === "phase_end"
  ) {
    return event.phase;
  }
  return null;
}
