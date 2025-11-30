"use client"

import { motion, AnimatePresence } from "framer-motion"
import { Brain } from "lucide-react"
import { cn } from "@/lib/utils"

interface ThinkingStage {
  id: string
  label: string
  status: "pending" | "active" | "done"
}

interface ThinkingStreamProps {
  stages: ThinkingStage[]
  mode?: "thinking" | "streaming_final" | "complete"
  finalContent?: string
  onViewProcess?: () => void
}

export function ThinkingStream({
  stages = [],
  mode = "thinking",
  finalContent,
  onViewProcess
}: ThinkingStreamProps) {

  if (mode === "complete") {
    return (
      <div className="rounded-2xl bg-background px-3 py-2 border text-sm">
        <p className="whitespace-pre-wrap">{finalContent}</p>
        <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
          <span>Created by multi-model collaborate engine.</span>
          {onViewProcess && (
            <button
              type="button"
              className="underline underline-offset-2 hover:text-foreground transition-colors"
              onClick={onViewProcess}
            >
              View how this was generated
            </button>
          )}
        </div>
      </div>
    )
  }

  if (mode === "streaming_final") {
    return (
      <div className="rounded-2xl bg-muted/50 px-3 py-2 border text-sm">
        {/* Progress indicator */}
        <div className="mb-2 flex items-center gap-2 text-[11px] text-muted-foreground">
          <TypingDots />
          <span>Final answer synthesizing…</span>
        </div>
        <p className="whitespace-pre-wrap">{finalContent}</p>
      </div>
    )
  }

  // Default: thinking mode
  return (
    <div className="rounded-2xl bg-muted/50 px-3 py-2 border text-xs">
      {/* Header */}
      <div className="mb-3 flex items-center gap-2 text-[11px] text-muted-foreground">
        <TypingDots />
        <span>Syntra is collaborating across models…</span>
      </div>

      {/* Thinking Stages */}
      <div className="space-y-2">
        <AnimatePresence>
          {stages.map((stage, index) => (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: index * 0.1 }}
              className="flex items-center gap-2"
            >
              {/* Stage Status Indicator */}
              {stage.status === "pending" && (
                <div className="h-1.5 w-1.5 rounded-full bg-slate-400" />
              )}
              {stage.status === "active" && (
                <motion.div
                  className="h-1.5 w-1.5 rounded-full bg-sky-500"
                  animate={{ opacity: [0.2, 1, 0.2] }}
                  transition={{ duration: 1.2, repeat: Infinity }}
                />
              )}
              {stage.status === "done" && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.2 }}
                  className="h-1.5 w-1.5 rounded-full bg-emerald-500"
                />
              )}

              {/* Stage Label */}
              <span
                className={cn(
                  "text-[11px] transition-colors duration-200",
                  stage.status === "active"
                    ? "font-medium text-sky-700 dark:text-sky-300"
                    : "text-muted-foreground"
                )}
              >
                {stage.label}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Animated progress bar */}
      <motion.div
        className="mt-3 h-1 w-full rounded-full bg-gradient-to-r from-transparent via-slate-300 dark:via-slate-600 to-transparent"
        animate={{
          backgroundPosition: ['0% 50%', '100% 50%', '0% 50%']
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: 'linear'
        }}
        style={{
          backgroundSize: '200% 100%'
        }}
      />
    </div>
  )
}

// Animated typing dots component
function TypingDots() {
  return (
    <div className="flex gap-0.5">
      {[0, 1, 2].map(i => (
        <motion.span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-sky-500"
          animate={{ opacity: [0.2, 1, 0.2] }}
          transition={{
            repeat: Infinity,
            duration: 1,
            delay: i * 0.2,
          }}
        />
      ))}
    </div>
  )
}