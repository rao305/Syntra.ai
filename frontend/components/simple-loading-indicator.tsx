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
          <div className="px-1 py-2">
            {/* Simple text loading indicator */}
            <div className="flex items-center gap-2">
              {/* Minimal animated dots */}
              <div className="flex gap-1">
                <motion.div
                  className="w-1 h-1 rounded-full bg-zinc-400"
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: 0 }}
                />
                <motion.div
                  className="w-1 h-1 rounded-full bg-zinc-400"
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: 0.15 }}
                />
                <motion.div
                  className="w-1 h-1 rounded-full bg-zinc-400"
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: 0.3 }}
                />
              </div>

              {/* Stage and model info */}
              <p className="text-xs text-zinc-500">
                {stageName} <span className="text-zinc-400 font-medium ml-1">({modelName})</span>
              </p>
            </div>

            {/* Expandable output section */}
            {modelOutput && (
              <AnimatePresence>
                <div className="pt-1.5">
                  <button
                    onClick={() => setIsOutputExpanded(!isOutputExpanded)}
                    className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
                  >
                    <span>View output</span>
                    <ChevronDown
                      className="w-3 h-3 transition-transform"
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
                      className="mt-1.5 overflow-hidden"
                    >
                      <p className="text-xs text-zinc-400 leading-relaxed whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
                        {modelOutput}
                      </p>
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
