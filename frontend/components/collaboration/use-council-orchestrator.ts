'use client'

import { useState, useCallback, useRef, useEffect } from 'react'

type OutputMode = 'deliverable-only' | 'deliverable-ownership' | 'audit' | 'full-transcript'
type CouncilStatus = 'idle' | 'pending' | 'running' | 'success' | 'error' | 'cancelled'
type Phase = 'phase_1_start' | 'phase_1_complete' | 'phase_2_start' | 'phase_2_complete' | 'phase_3_start' | 'phase_3_complete'

export interface UseCouncilOrchestratorState {
  sessionId: string | null
  status: CouncilStatus
  currentPhase: Phase | null
  output: string | null
  error: string | null
  executionTimeMs: number | null
  isRunning: boolean
}

export function useCouncilOrchestrator() {
  const [state, setState] = useState<UseCouncilOrchestratorState>({
    sessionId: null,
    status: 'idle',
    currentPhase: null,
    output: null,
    error: null,
    executionTimeMs: null,
    isRunning: false,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Start council execution
  const startCouncil = useCallback(
    async (
      query: string,
      orgId: string,
      outputMode: OutputMode = 'deliverable-ownership',
      preferredProviders?: Record<string, string>
    ) => {
      try {
        setState((prev) => ({
          ...prev,
          status: 'pending',
          error: null,
          output: null,
          isRunning: true,
        }))

        abortRef.current = new AbortController()

        const response = await fetch('/api/council/orchestrate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-org-id': orgId,
          },
          body: JSON.stringify({
            query,
            output_mode: outputMode,
            preferred_providers: preferredProviders,
          }),
          signal: abortRef.current.signal,
        })

        if (!response.ok) {
          throw new Error(`Failed to start council: ${response.statusText}`)
        }

        const data = await response.json()
        setState((prev) => ({
          ...prev,
          sessionId: data.session_id,
          status: 'running',
        }))

        // Connect WebSocket for updates
        connectWebSocket(data.session_id, orgId)
      } catch (err) {
        const error = err instanceof Error ? err.message : 'Unknown error'
        setState((prev) => ({
          ...prev,
          status: 'error',
          error,
          isRunning: false,
        }))
      }
    },
    []
  )

  // Connect to WebSocket for real-time updates
  const connectWebSocket = useCallback((sessionId: string, orgId: string) => {
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${typeof window !== 'undefined' ? window.location.host : 'localhost:8000'}/api/council/ws/${sessionId}`

    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onmessage = (event) => {
      const message = JSON.parse(event.data)

      if (message.type === 'progress') {
        setState((prev) => ({
          ...prev,
          currentPhase: message.current_phase,
        }))
      } else if (message.type === 'complete') {
        setState((prev) => ({
          ...prev,
          status: message.status,
          output: message.output,
          error: message.error,
          executionTimeMs: message.execution_time_ms,
          isRunning: false,
        }))
      } else if (message.type === 'error') {
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: message.error,
          isRunning: false,
        }))
      }
    }

    wsRef.current.onerror = () => {
      setState((prev) => ({
        ...prev,
        status: 'error',
        error: 'WebSocket connection error',
        isRunning: false,
      }))
    }

    wsRef.current.onclose = () => {
      wsRef.current = null
    }
  }, [])

  // Cancel running council
  const cancelCouncil = useCallback(async (orgId: string) => {
    if (!state.sessionId) return

    try {
      abortRef.current?.abort()

      await fetch(`/api/council/orchestrate/${state.sessionId}`, {
        method: 'DELETE',
        headers: {
          'x-org-id': orgId,
        },
      })

      setState((prev) => ({
        ...prev,
        status: 'cancelled',
        isRunning: false,
      }))

      if (wsRef.current) {
        wsRef.current.close()
      }
    } catch (err) {
      console.error('Failed to cancel council:', err)
    }
  }, [state.sessionId])

  // Reset state
  const reset = useCallback(() => {
    setState({
      sessionId: null,
      status: 'idle',
      currentPhase: null,
      output: null,
      error: null,
      executionTimeMs: null,
      isRunning: false,
    })
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      abortRef.current?.abort()
    }
  }, [])

  return {
    ...state,
    startCouncil,
    cancelCouncil,
    reset,
  }
}
