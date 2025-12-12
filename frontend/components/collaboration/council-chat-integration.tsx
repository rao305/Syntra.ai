'use client'

import { useState, useRef, useEffect } from 'react'
import { Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CouncilOrchestration } from './council-orchestration'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

interface CouncilChatIntegrationProps {
  query: string
  orgId: string
  threadId?: string
  onFinalAnswer: (answer: string) => void
  onCancel: () => void
}

/**
 * Displays the Council Orchestration modal inline with the chat.
 * Once complete, the final answer is displayed in the chat.
 */
export function CouncilChatIntegration({
  query,
  orgId,
  threadId,
  onFinalAnswer,
  onCancel,
}: CouncilChatIntegrationProps) {
  const [isOpen, setIsOpen] = useState(true)
  const finalAnswerRef = useRef<string | null>(null)

  const handleComplete = (output: string) => {
    finalAnswerRef.current = output
  }

  const handleClose = () => {
    setIsOpen(false)
    if (finalAnswerRef.current) {
      onFinalAnswer(finalAnswerRef.current)
    } else {
      onCancel()
    }
  }

  return (
    <AlertDialog open={isOpen}>
      <AlertDialogContent className="max-w-6xl h-[90vh] p-0 border-0 gap-0">
        <AlertDialogHeader className="p-4 border-b border-slate-200 dark:border-slate-700">
          <AlertDialogTitle>Council Orchestration</AlertDialogTitle>
          <AlertDialogDescription>
            Multi-agent collaboration analyzing your query...
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="flex-1 overflow-hidden">
          <CouncilOrchestration
            query={query}
            orgId={orgId}
            onComplete={handleComplete}
            onClose={handleClose}
          />
        </div>
      </AlertDialogContent>
    </AlertDialog>
  )
}

/**
 * Chat input extension showing collaboration button.
 * Replaces the old mode selector (auto/manual).
 */
interface CollaborationInputExtensionProps {
  isLoading: boolean
  disabled?: boolean
  onCollaborationClick: () => void
}

export function CollaborationInputExtension({
  isLoading,
  disabled = false,
  onCollaborationClick,
}: CollaborationInputExtensionProps) {
  return (
    <button
      onClick={onCollaborationClick}
      disabled={isLoading || disabled}
      title="Open Council Orchestration for multi-agent collaboration"
      className={cn(
        'inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm',
        'bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800',
        'dark:from-purple-700 dark:to-purple-800 dark:hover:from-purple-800 dark:hover:to-purple-900',
        'text-white shadow-lg hover:shadow-xl transition-all',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        isLoading && 'animate-pulse'
      )}
    >
      <Zap className="w-4 h-4" />
      <span>Collaborate</span>
    </button>
  )
}

/**
 * Final answer display component for chat.
 * Shows the complete council output with syntax highlighting.
 */
interface CouncilFinalAnswerProps {
  answer: string
  executionTimeMs?: number
}

export function CouncilFinalAnswer({
  answer,
  executionTimeMs,
}: CouncilFinalAnswerProps) {
  return (
    <div className="space-y-3">
      {/* Metadata */}
      {executionTimeMs && (
        <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
          <Zap className="w-3 h-3" />
          <span>
            Council executed in{' '}
            <span className="font-mono font-semibold">
              {(executionTimeMs / 1000).toFixed(1)}s
            </span>
          </span>
        </div>
      )}

      {/* Final Answer */}
      <div className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-3">
        <h4 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
          Final Deliverable
        </h4>

        <div className="overflow-x-auto">
          <pre className="text-xs text-slate-700 dark:text-slate-300 font-mono whitespace-pre-wrap word-break break-words">
            {answer}
          </pre>
        </div>
      </div>
    </div>
  )
}
