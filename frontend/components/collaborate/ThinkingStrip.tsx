/**
 * ThinkingStrip Component (Abstracted Phase UI)
 *
 * Displays the collaborative reasoning process as a single animated thinking card.
 * Shows 5 user-facing phases that group internal roles:
 * 1. Understanding your query (analyst + creator)
 * 2. Researching recent data (researcher)
 * 3. Refining and organizing (critic + internal_synth)
 * 4. Cross-checking with AI models (council)
 * 5. Synthesizing final report (director)
 *
 * Props:
 * - steps: Current state of each thinking phase
 * - currentIndex: Which phase is currently active (0–4)
 * - councilSummary: Progress info for the cross-check phase
 * - isCollapsed: Whether to collapse after thinking is complete
 * - onToggleCollapsed: Callback when user clicks hide/show button
 */

import React, { useMemo } from "react";
import { PHASE_LABELS, AbstractPhase } from "@/types/collaborate-events";

export type ThinkingStatus = "pending" | "active" | "done";

/**
 * Represents a single thinking phase step
 */
export interface ThinkingStep {
  phase: AbstractPhase; // "understand" | "research" | "reason_refine" | "crosscheck" | "synthesize"
  label: string; // e.g., "Understanding your query"
  modelDisplay?: string; // e.g., "GPT-4.1" or "Perplexity, Gemini, GPT, Kimi, OpenRouter"
  status: ThinkingStatus;
  preview: string; // Last snippet of output
  latency_ms?: number;
}

export interface CouncilSummary {
  completed: number;
  total: number;
  stanceCounts?: {
    agree: number;
    mixed: number;
    disagree: number;
  };
}

export interface ThinkingStripProps {
  steps: ThinkingStep[];
  currentIndex: number;
  councilSummary?: CouncilSummary;
  isCollapsed?: boolean;
  onToggleCollapsed?: () => void;
}

/**
 * Main ThinkingStrip component
 */
export function ThinkingStrip({
  steps,
  currentIndex,
  councilSummary,
  isCollapsed = false,
  onToggleCollapsed,
}: ThinkingStripProps) {
  const totalSteps = steps.length;

  const currentStepLabel = useMemo(
    () => steps[currentIndex]?.label ?? "Working...",
    [steps, currentIndex]
  );

  if (!steps.length) return null;

  return (
    <div className="mb-4 overflow-hidden rounded-2xl border border-slate-700 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 text-slate-50 shadow-xl">
      {/* Header row - always visible */}
      <div className="flex items-center justify-between gap-3 border-b border-slate-700/50 px-4 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Brain emoji icon */}
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-cyan-500 shadow-lg">
            <span className="text-base">🧠</span>
          </div>

          {/* Status text */}
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-semibold uppercase tracking-widest text-slate-300">
              AI Team Collaborating
            </span>
            <span className="text-sm text-slate-400 truncate">
              Step {currentIndex + 1} of {totalSteps} — {currentStepLabel}
            </span>
          </div>
        </div>

        {/* Collapse button */}
        {onToggleCollapsed && (
          <button
            onClick={onToggleCollapsed}
            className="flex-shrink-0 rounded-lg border border-slate-600 bg-slate-800/40 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700/60 hover:border-slate-500 transition-colors"
          >
            {isCollapsed ? "Show" : "Hide"}
          </button>
        )}
      </div>

      {/* Expanded content */}
      {!isCollapsed && (
        <div className="space-y-2 px-4 py-3 max-h-96 overflow-y-auto">
          {steps.map((step, idx) => {
            const isActive = step.status === "active";
            const isDone = step.status === "done";
            const isPending = step.status === "pending";

            return (
              <div
                key={step.phase}
                className="flex items-start gap-3 text-xs transition-colors"
              >
                {/* Timeline bullet and connector */}
                <div className="flex flex-col items-center flex-shrink-0 pt-1">
                  {/* Status indicator dot */}
                  <div
                    className={[
                      "h-3 w-3 rounded-full transition-all",
                      isActive
                        ? "animate-pulse bg-gradient-to-r from-cyan-400 to-sky-400 shadow-lg shadow-sky-500/50"
                        : isDone
                        ? "bg-gradient-to-r from-emerald-400 to-green-400"
                        : isPending
                        ? "bg-slate-600"
                        : "bg-slate-500",
                    ].join(" ")}
                  />

                  {/* Vertical connector to next step */}
                  {idx < steps.length - 1 && (
                    <div
                      className={[
                        "mt-2 h-5 w-px transition-colors",
                        isDone
                          ? "bg-slate-600"
                          : isActive || isPending
                          ? "bg-slate-700"
                          : "bg-slate-700",
                      ].join(" ")}
                    />
                  )}
                </div>

                {/* Step content */}
                <div className="flex-1 min-w-0 py-1">
                  {/* Step label + model */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={[
                        "font-semibold transition-colors",
                        isActive
                          ? "text-cyan-300"
                          : isDone
                          ? "text-emerald-300"
                          : "text-slate-300",
                      ].join(" ")}
                    >
                      {step.label}
                    </span>

                    {step.modelDisplay && (
                      <span className="text-[11px] text-slate-500">
                        · {step.modelDisplay}
                      </span>
                    )}

                    {/* Status badge */}
                    {isActive && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-cyan-500/20 px-2 py-0.5 text-[10px] text-cyan-300 border border-cyan-500/30">
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
                        Thinking…
                      </span>
                    )}

                    {isDone && step.latency_ms && (
                      <span className="text-[10px] text-slate-500">
                        {(step.latency_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>

                  {/* Preview text */}
                  {step.preview && (
                    <p className="mt-1 line-clamp-2 text-[11px] text-slate-400 leading-snug">
                      {step.preview}
                    </p>
                  )}

                  {/* Council summary (only shown for crosscheck phase) */}
                  {step.phase === "crosscheck" && councilSummary && (
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-slate-800/60 px-2 py-0.5 text-[10px] text-slate-300 border border-slate-700">
                        {councilSummary.completed}/{councilSummary.total} reviews
                      </span>

                      {councilSummary.stanceCounts && (
                        <>
                          {councilSummary.stanceCounts.agree > 0 && (
                            <span className="rounded-full bg-emerald-900/50 px-2 py-0.5 text-[10px] text-emerald-300 border border-emerald-700/50">
                              ✓ {councilSummary.stanceCounts.agree} agree
                            </span>
                          )}
                          {councilSummary.stanceCounts.mixed > 0 && (
                            <span className="rounded-full bg-amber-900/50 px-2 py-0.5 text-[10px] text-amber-300 border border-amber-700/50">
                              ◆ {councilSummary.stanceCounts.mixed} mixed
                            </span>
                          )}
                          {councilSummary.stanceCounts.disagree > 0 && (
                            <span className="rounded-full bg-red-900/50 px-2 py-0.5 text-[10px] text-red-300 border border-red-700/50">
                              ✕ {councilSummary.stanceCounts.disagree} disagree
                            </span>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Expanded view of thinking transcript (for detailed inspection)
 * Use this in a modal/drawer if you want users to inspect all thinking details
 */
export function ThinkingTranscript({ steps }: { steps: ThinkingStep[] }) {
  return (
    <div className="space-y-4">
      {steps.map((step) => (
        <div
          key={step.phase}
          className="rounded-lg border border-slate-700 bg-slate-900/50 p-3"
        >
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-100">
              {step.label}
            </h3>
            {step.latency_ms && (
              <span className="text-[11px] text-slate-500">
                {(step.latency_ms / 1000).toFixed(2)}s
              </span>
            )}
          </div>
          {step.modelDisplay && (
            <p className="text-[11px] text-slate-400">{step.modelDisplay}</p>
          )}
          {step.preview && (
            <p className="mt-2 text-xs text-slate-300 whitespace-pre-wrap">
              {step.preview}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
