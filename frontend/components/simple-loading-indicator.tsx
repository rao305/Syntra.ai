"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";

interface SimpleLoadingIndicatorProps {
  modelName?: string;
  stageName?: string;
  modelOutput?: string;
  isVisible?: boolean;
}

export function SimpleLoadingIndicator({
  modelName = "Processing",
  stageName = "Processing your request…",
  modelOutput,
  isVisible = true,
}: SimpleLoadingIndicatorProps) {
  const [isOutputExpanded, setIsOutputExpanded] = useState(false);

  return (
    <AnimatePresence mode="wait">
      {isVisible && (
        <motion.div
          key="loading"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.3 }}
          className="w-full"
        >
          <div className="rounded-lg border border-zinc-700/50 bg-zinc-900/40 px-4 py-3 space-y-2.5">
            {/* Main loading indicator */}
            <div className="flex items-center gap-3">
              {/* Animated spinner with three dots */}
              <div className="flex gap-1.5">
                <motion.div
                  className="h-1.5 w-1.5 rounded-full bg-zinc-500"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: 0 }}
                />
                <motion.div
                  className="h-1.5 w-1.5 rounded-full bg-zinc-500"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: 0.15 }}
                />
                <motion.div
                  className="h-1.5 w-1.5 rounded-full bg-zinc-500"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: 0.3 }}
                />
              </div>

              {/* Stage and model info */}
              <div className="flex-1">
                <p className="text-sm font-medium text-zinc-200">{stageName}</p>
                <p className="text-xs text-zinc-400">Running on {modelName}</p>
              </div>
            </div>

            {/* Expandable output section */}
            {modelOutput && (
              <AnimatePresence>
                <div className="border-t border-zinc-700/30 pt-2.5">
                  <button
                    onClick={() => setIsOutputExpanded(!isOutputExpanded)}
                    className="flex items-center gap-2 text-xs text-zinc-400 hover:text-zinc-300 transition-colors w-full"
                  >
                    <span>View Output</span>
                    <ChevronDown
                      className="w-3.5 h-3.5 transition-transform"
                      style={{
                        transform: isOutputExpanded ? "rotate(180deg)" : "rotate(0deg)",
                      }}
                    />
                  </button>

                  {isOutputExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                      className="mt-2 overflow-hidden"
                    >
                      <div className="bg-zinc-950/60 rounded-md p-3 border border-zinc-700/30">
                        <p className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
                          {modelOutput}
                        </p>
                      </div>
                    </motion.div>
                  )}
                </div>
              </AnimatePresence>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
