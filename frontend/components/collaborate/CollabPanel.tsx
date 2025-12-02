"use client"

import { motion } from "framer-motion"

export type CollabStageId = "analyst" | "researcher" | "creator" | "critic" | "council" | "synth"

export interface CollabStageState {
  id: CollabStageId
  label: string
  model: string  // now represents the dynamically selected model ID (e.g., "gpt-4o", "gemini-2.0")
  status: "pending" | "running" | "done" | "error"
  preview?: string
  duration_ms?: number
}

export interface CollabPanelState {
  active: boolean
  stages: CollabStageState[]
}

interface CollabPanelProps {
  state: CollabPanelState
}

export function CollabPanel({ state }: CollabPanelProps) {
  if (!state.active) return null

  const currentIndex = state.stages.findIndex((s) => s.status === "running")
  const completedCount = state.stages.filter((s) => s.status === "done").length
  const total = state.stages.length
  const progress = (completedCount / total) * 100

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      className="mb-4 rounded-xl border border-emerald-900/50 bg-gradient-to-br from-emerald-950/40 to-emerald-900/20 p-4 shadow-lg backdrop-blur-sm"
    >
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <motion.span
            className="inline-flex h-2 w-2 rounded-full bg-emerald-400"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          <p className="text-sm font-semibold text-emerald-100">
            AI Team is collaborating…
          </p>
        </div>
        <p className="text-xs text-emerald-300/70">
          {completedCount}/{total} stages
        </p>
      </div>

      {/* Progress bar */}
      <div className="mb-3 h-1 w-full overflow-hidden rounded-full bg-emerald-950/60">
        <motion.div
          className="h-full bg-gradient-to-r from-emerald-400 to-emerald-500"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ type: "spring", stiffness: 50, damping: 20 }}
        />
      </div>

      {/* Stages */}
      <div className="space-y-2">
        {state.stages.map((stage) => {
          const isRunning = stage.status === "running"
          const isDone = stage.status === "done"

          return (
            <motion.div
              key={stage.id}
              layout
              className="flex items-start gap-3 rounded-lg border border-emerald-800/30 bg-emerald-900/20 px-3 py-2"
            >
              {/* Model indicator */}
              <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-emerald-900/60 text-[10px] font-bold uppercase tracking-wide text-emerald-200">
                {stage.model === "?" ? "?" : stage.model.split("-")[0].slice(0, 2)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-semibold text-emerald-100">
                    {stage.label}
                  </p>
                  {stage.model !== "?" && (
                    <span className="text-[10px] uppercase tracking-wide text-emerald-400/70 font-mono">
                      • {stage.model}
                    </span>
                  )}
                  {isRunning && (
                    <motion.span
                      className="text-[10px] text-emerald-300"
                      animate={{ opacity: [0.5, 1, 0.5] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    >
                      Thinking…
                    </motion.span>
                  )}
                  {isDone && stage.duration_ms && (
                    <span className="text-[10px] text-emerald-400/70">
                      {(stage.duration_ms / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>

                {/* Preview text */}
                {stage.preview && (
                  <p className="mt-1 line-clamp-1 text-xs text-emerald-200/80">
                    {stage.preview}
                  </p>
                )}
              </div>

              {/* Status indicator */}
              <div className="mt-1 flex-shrink-0">
                {isRunning && (
                  <motion.span
                    className="inline-flex h-2 w-2 rounded-full bg-emerald-400"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 1, repeat: Infinity }}
                  />
                )}
                {isDone && (
                  <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                )}
                {!isRunning && !isDone && (
                  <span className="inline-flex h-2 w-2 rounded-full bg-emerald-800/40" />
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}
