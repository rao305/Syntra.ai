"use client"

import { Brain } from "lucide-react"
import { motion } from "framer-motion"

interface CollaborateToggleProps {
  isCollaborateMode: boolean
  toggleCollaborateMode: () => void
  mode: string
  setMode: (mode: string) => void
}

export function CollaborateToggle({
  isCollaborateMode,
  toggleCollaborateMode,
  mode,
  setMode
}: CollaborateToggleProps) {
  return (
    <div className="flex items-center gap-2">
      {/* Collaborate Button */}
      <motion.button
        onClick={() => {
          if (isCollaborateMode) {
            toggleCollaborateMode()
          } else {
            toggleCollaborateMode()
          }
        }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm font-medium ${
          isCollaborateMode
            ? "bg-emerald-600 text-white"
            : "text-zinc-400 hover:bg-zinc-800"
        }`}
      >
        <Brain className="w-4 h-4" />
        <span>Collaborate</span>
      </motion.button>

      {/* Auto | Manual Buttons - Only show when collaboration is enabled */}
      {isCollaborateMode && (
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -10 }}
          transition={{ duration: 0.2 }}
          className="flex items-center gap-1 bg-zinc-800 rounded-lg p-1"
        >
          {/* Auto Button */}
          <motion.button
            onClick={() => setMode("auto")}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`px-3 py-1.5 rounded transition-colors text-sm font-medium ${
              mode === "auto"
                ? "bg-emerald-600 text-white"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Auto
          </motion.button>

          {/* Divider */}
          <div className="w-px h-4 bg-zinc-600" />

          {/* Manual Button */}
          <motion.button
            onClick={() => setMode("manual")}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`px-3 py-1.5 rounded transition-colors text-sm font-medium ${
              mode === "manual"
                ? "bg-blue-600 text-white"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Manual
          </motion.button>
        </motion.div>
      )}
    </div>
  )
}
