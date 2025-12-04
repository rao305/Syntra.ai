"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  StageId,
  StageState,
} from "@/lib/collabStages";

const stageText: Record<StageId, string> = {
  analyst: "Analyzing your query…",
  researcher: "Researching across sources…",
  creator: "Drafting a structured answer…",
  critic: "Checking for gaps & issues…",
  council: "Running LLM council vote…",
  synthesizer: "Synthesizing final response…",
};

interface CollaborateTimelineProps {
  stages?: StageState[];
}

export function CollaborateTimeline({ stages = [] }: CollaborateTimelineProps) {
  const [localStages, setLocalStages] = useState<StageState[]>(stages);

  useEffect(() => {
    setLocalStages(stages);
  }, [stages]);

  // Get the current active (running) stage - only show the current one
  const activeStage = localStages.find((s) => s.status === "running");

  return (
    <AnimatePresence mode="wait">
      {activeStage && (
        <motion.div
          key={activeStage.id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.3 }}
          className="w-full"
        >
          <div className="rounded-3xl border border-emerald-500/15 bg-emerald-950/60 px-5 py-4">
            <div className="flex items-center gap-3">
              {/* Animated spinner with three dots */}
              <div className="flex gap-1.5">
                <motion.div
                  className="h-2 w-2 rounded-full bg-emerald-400"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: 0 }}
                />
                <motion.div
                  className="h-2 w-2 rounded-full bg-emerald-400"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: 0.15 }}
                />
                <motion.div
                  className="h-2 w-2 rounded-full bg-emerald-400"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: 0.3 }}
                />
              </div>

              {/* Stage info */}
              <div className="flex-1">
                <p className="text-sm font-medium text-emerald-100">
                  {stageText[activeStage.id]}
                </p>
                {activeStage.modelName && (
                  <p className="text-xs text-emerald-400/70">
                    Running on {activeStage.modelName}
                  </p>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
