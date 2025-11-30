"use client"

import { useCallback, useState } from 'react'
import {
  CollaborateEvent,
  PhaseStartEvent,
  PhaseEndEvent,
  PhaseDeltaEvent,
  AbstractPhase,
  PHASE_INDICES,
  TOTAL_PHASES,
} from '@/types/collaborate-events'
import { ThinkingStep, CouncilSummary } from '@/components/collaborate/ThinkingStrip'

interface UsePhaseCollaborationProps {
  onPhaseUpdate?: (phase: AbstractPhase, step: ThinkingStep) => void
  onCouncilProgress?: (summary: CouncilSummary) => void
  onFinalAnswerStart?: () => void
  onFinalAnswerDelta?: (textDelta: string) => void
  onFinalAnswerComplete?: (response: any) => void
  onError?: (error: string) => void
}

/**
 * Hook for managing phase-based collaboration streaming.
 * Maintains the state of the 5 abstract phases and handles events.
 */
export function usePhaseCollaboration({
  onPhaseUpdate,
  onCouncilProgress,
  onFinalAnswerStart,
  onFinalAnswerDelta,
  onFinalAnswerComplete,
  onError,
}: UsePhaseCollaborationProps) {
  const [phases, setPhases] = useState<Record<AbstractPhase, ThinkingStep>>({
    understand: {
      phase: 'understand',
      label: 'Understanding your query',
      status: 'pending',
      preview: '',
    },
    research: {
      phase: 'research',
      label: 'Researching recent data and trends',
      status: 'pending',
      preview: '',
    },
    reason_refine: {
      phase: 'reason_refine',
      label: 'Refining and organizing the answer',
      status: 'pending',
      preview: '',
    },
    crosscheck: {
      phase: 'crosscheck',
      label: 'Cross-checking with other AI models',
      status: 'pending',
      preview: '',
    },
    synthesize: {
      phase: 'synthesize',
      label: 'Synthesizing final report',
      status: 'pending',
      preview: '',
    },
  })

  const [councilSummary, setCouncilSummary] = useState<CouncilSummary>({
    completed: 0,
    total: 0,
    stanceCounts: { agree: 0, mixed: 0, disagree: 0 },
  })

  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0)

  const handlePhaseStart = useCallback(
    (event: PhaseStartEvent) => {
      const phase = event.phase
      setPhases((prev) => ({
        ...prev,
        [phase]: {
          ...prev[phase],
          label: event.label,
          modelDisplay: event.model_display,
          status: 'active' as const,
        },
      }))
      setCurrentPhaseIndex(event.step_index)
      onPhaseUpdate?.(phase, {
        ...phases[phase],
        label: event.label,
        modelDisplay: event.model_display,
        status: 'active',
      })
    },
    [onPhaseUpdate, phases]
  )

  const handlePhaseDelta = useCallback((event: PhaseDeltaEvent) => {
    const phase = event.phase
    setPhases((prev) => ({
      ...prev,
      [phase]: {
        ...prev[phase],
        preview: event.text_delta,
      },
    }))
  }, [])

  const handlePhaseEnd = useCallback(
    (event: PhaseEndEvent) => {
      const phase = event.phase
      setPhases((prev) => ({
        ...prev,
        [phase]: {
          ...prev[phase],
          status: 'done' as const,
          latency_ms: event.latency_ms,
        },
      }))
      onPhaseUpdate?.(phase, {
        ...phases[phase],
        status: 'done',
        latency_ms: event.latency_ms,
      })
    },
    [onPhaseUpdate, phases]
  )

  const handleCouncilProgress = useCallback(
    (event: any) => {
      const summary: CouncilSummary = {
        completed: event.completed,
        total: event.total,
        stanceCounts: event.stance_counts,
      }
      setCouncilSummary(summary)
      onCouncilProgress?.(summary)
    },
    [onCouncilProgress]
  )

  const handleFinalAnswerDelta = useCallback(
    (text: string) => {
      onFinalAnswerDelta?.(text)
    },
    [onFinalAnswerDelta]
  )

  const handleFinalAnswerDone = useCallback(
    (response: any) => {
      onFinalAnswerComplete?.(response)
    },
    [onFinalAnswerComplete]
  )

  const handleError = useCallback(
    (message: string) => {
      onError?.(message)
    },
    [onError]
  )

  const processEvent = useCallback(
    (event: CollaborateEvent) => {
      switch (event.type) {
        case 'phase_start':
          handlePhaseStart(event as PhaseStartEvent)
          break
        case 'phase_delta':
          handlePhaseDelta(event as PhaseDeltaEvent)
          break
        case 'phase_end':
          handlePhaseEnd(event as PhaseEndEvent)
          break
        case 'council_progress':
          handleCouncilProgress(event)
          break
        case 'final_answer_delta':
          handleFinalAnswerDelta(event.text_delta)
          break
        case 'final_answer_done':
          handleFinalAnswerDone(event.response)
          break
        case 'error':
          handleError(event.message || 'Unknown error')
          break
        // Ignore detailed stage events - they're for internal logging only
        case 'stage_start':
        case 'stage_delta':
        case 'stage_end':
          break
      }
    },
    [
      handlePhaseStart,
      handlePhaseDelta,
      handlePhaseEnd,
      handleCouncilProgress,
      handleFinalAnswerDelta,
      handleFinalAnswerDone,
      handleError,
    ]
  )

  const getPhasesList = useCallback((): ThinkingStep[] => {
    return Object.values(phases)
  }, [phases])

  return {
    // State
    phases,
    councilSummary,
    currentPhaseIndex,

    // Methods
    processEvent,
    getPhasesList,

    // Handlers
    handlePhaseStart,
    handlePhaseDelta,
    handlePhaseEnd,
    handleCouncilProgress,
  }
}
