'use client'

import { CollaborationAttribution } from '@/components/collaboration-attribution'
import { EnhancedMessageContent } from '@/components/enhanced-message-content'
import { ResponseMetrics } from '@/components/response-metrics'
import { cn } from '@/lib/utils'
import { ChevronDown, ChevronRight, Zap } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

type AgentName =
  | 'Optimizer Agent'
  | 'Red Teamer Agent'
  | 'Data Engineer Agent'
  | 'Researcher Agent'
  | 'Architect Agent'
  | 'Debate Synthesizer'
  | 'Judge Agent'
  | 'Final Answer'

interface AgentOutput {
  name: AgentName
  duration: number
  output?: string
  status: 'pending' | 'running' | 'complete'
  phase: 'phase_1' | 'phase_2' | 'phase_3' | 'final'
  startTime?: number
}

interface OrchestrationMessageProps {
  query: string
  orgId: string
  sessionId: string
  onComplete: (output: string) => void
  initialAgents?: AgentOutput[]
  currentPhase?: string
  finalAnswer?: string
  isCompleted?: boolean // New prop to prevent reconnection for completed sessions
}

const AGENT_COLORS: Record<AgentName, string> = {
  'Optimizer Agent': 'bg-blue-500/20 border-blue-500/50',
  'Red Teamer Agent': 'bg-red-500/20 border-red-500/50',
  'Data Engineer Agent': 'bg-purple-500/20 border-purple-500/50',
  'Researcher Agent': 'bg-cyan-500/20 border-cyan-500/50',
  'Architect Agent': 'bg-emerald-500/20 border-emerald-500/50',
  'Debate Synthesizer': 'bg-orange-500/20 border-orange-500/50',
  'Judge Agent': 'bg-pink-500/20 border-pink-500/50',
  'Final Answer': 'bg-green-500/20 border-green-500/50',
}

// Track completed sessions globally to prevent reconnection across component remounts
const completedSessions = new Set<string>()

export function OrchestrationMessage({
  query,
  orgId,
  sessionId,
  onComplete,
  initialAgents,
  currentPhase,
  finalAnswer: initialFinalAnswer,
  isCompleted: propIsCompleted,
}: OrchestrationMessageProps) {
  const [agents, setAgents] = useState<AgentOutput[]>(
    initialAgents || [
      { name: 'Optimizer Agent', duration: 0, status: 'pending', phase: 'phase_1' },
      { name: 'Red Teamer Agent', duration: 0, status: 'pending', phase: 'phase_1' },
      { name: 'Data Engineer Agent', duration: 0, status: 'pending', phase: 'phase_1' },
      { name: 'Researcher Agent', duration: 0, status: 'pending', phase: 'phase_1' },
      { name: 'Architect Agent', duration: 0, status: 'pending', phase: 'phase_1' },
      { name: 'Debate Synthesizer', duration: 0, status: 'pending', phase: 'phase_2' },
      { name: 'Judge Agent', duration: 0, status: 'pending', phase: 'phase_3' },
      { name: 'Final Answer', duration: 0, status: 'pending', phase: 'final' },
    ]
  )
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [executionTime, setExecutionTime] = useState(0)
  const [finalAnswer, setFinalAnswer] = useState<string | null>(initialFinalAnswer || null)
  const [selectedAgent, setSelectedAgent] = useState<AgentName>('Optimizer Agent')
  const [wsConnected, setWsConnected] = useState(false)
  const [isSessionCompleted, setIsSessionCompleted] = useState(
    propIsCompleted || completedSessions.has(sessionId) || !!initialFinalAnswer
  )
  const wsRef = useRef<WebSocket | null>(null)
  const startTimeRef = useRef<number>(Date.now())
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const connectionAttemptedRef = useRef(false)
  const mountedRef = useRef(true)

  // Memoized completion handler to prevent recreating on each render
  const handleComplete = useCallback((output: string) => {
    if (!mountedRef.current) return

    // Mark session as completed globally
    completedSessions.add(sessionId)
    setIsSessionCompleted(true)
    setFinalAnswer(output)

    // Clean up WebSocket
    if (wsRef.current) {
      try {
        wsRef.current.close(1000, 'Session completed')
      } catch (e) {
        // Ignore close errors
      }
      wsRef.current = null
    }

    // Clear polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }

    onComplete(output)
  }, [sessionId, onComplete])

  // Connect to WebSocket for real-time updates, with fallback to polling
  useEffect(() => {
    // Early exit if session is already completed or connection was already attempted
    if (isSessionCompleted || completedSessions.has(sessionId)) {
      console.log(`Session ${sessionId} already completed, skipping WebSocket connection`)
      return
    }

    // Prevent multiple connection attempts for the same session
    // But allow reconnection if the WebSocket is closed
    if (connectionAttemptedRef.current && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log(`WebSocket already connected for session ${sessionId}, skipping`)
      return
    }
    connectionAttemptedRef.current = true
    mountedRef.current = true

    let wsConnectAttempts = 0
    const maxWsAttempts = 2
    let isCleanedUp = false

    const connectWebSocket = () => {
      if (isCleanedUp || !mountedRef.current) return

      // Get the backend API URL and convert to WebSocket URL
      const apiUrl = typeof window !== 'undefined' && process.env.NEXT_PUBLIC_API_URL
        ? process.env.NEXT_PUBLIC_API_URL
        : 'http://127.0.0.1:8000/api'

      // Convert http/https to ws/wss
      const wsProtocol = apiUrl.startsWith('https') ? 'wss:' : 'ws:'
      const apiHost = apiUrl.replace(/^https?:\/\//, '').replace(/\/api$/, '')
      const wsUrl = `${wsProtocol}//${apiHost}/api/council/ws/${sessionId}`

      console.log('Attempting WebSocket connection:', wsUrl)

      try {
        wsRef.current = new WebSocket(wsUrl)

        wsRef.current.onmessage = (event) => {
          if (isCleanedUp || !mountedRef.current) return

          try {
            const message = JSON.parse(event.data)
            console.log('WebSocket message received:', message.type, message)

            if (message.type === 'agent_update') {
              // Update agent status
              const agentName = message.agent
              const hasOutput = !!message.output
              const outputLength = message.output ? message.output.length : 0
              console.log(`Agent update: ${agentName} -> ${message.status}`, {
                hasOutput,
                outputLength,
                outputPreview: message.output ? message.output.substring(0, 100) + '...' : 'none'
              })
              setAgents((prev) =>
                prev.map((agent) =>
                  agent.name === agentName
                    ? {
                      ...agent,
                      status: message.status,
                      // Always use new output if provided, otherwise keep existing
                      output: message.output !== undefined && message.output !== null && message.output !== ''
                        ? message.output
                        : agent.output,
                      duration: message.duration || agent.duration,
                      // Set startTime when agent starts running
                      startTime: message.status === 'running' && !agent.startTime
                        ? Date.now()
                        : agent.startTime,
                    }
                    : agent
                )
              )
            } else if (message.type === 'phase_update') {
              // Update phase
              console.log('Phase update:', message.phase)
            } else if (message.type === 'complete') {
              // Orchestration complete
              const output = message.output || message.final_answer || ''

              console.log('Orchestration complete, final answer:', {
                hasOutput: !!output,
                outputLength: output?.length || 0,
                outputPreview: output ? output.substring(0, 100) + '...' : 'empty',
                messageKeys: Object.keys(message)
              })

              setAgents((prev) =>
                prev.map((agent) =>
                  agent.name === 'Final Answer'
                    ? { ...agent, status: 'complete', output: output || agent.output }
                    : agent
                )
              )

              // If output is missing, try polling fallback to get it from API
              if (output && output.trim() !== '') {
                handleComplete(output)
              } else {
                console.warn('Complete message received but no output found, fetching from API...')
                // Fetch from API as fallback
                const apiUrl = typeof window !== 'undefined' && process.env.NEXT_PUBLIC_API_URL
                  ? process.env.NEXT_PUBLIC_API_URL
                  : 'http://127.0.0.1:8000/api'

                fetch(`${apiUrl}/council/orchestrate/${sessionId}`, {
                  method: 'GET',
                  headers: { 'Content-Type': 'application/json' },
                })
                  .then(res => res.json())
                  .then(data => {
                    if (data.status === 'success' && data.output) {
                      console.log('Fetched output from API fallback, length:', data.output.length)
                      setAgents((prev) =>
                        prev.map((agent) =>
                          agent.name === 'Final Answer'
                            ? { ...agent, status: 'complete', output: data.output }
                            : agent
                        )
                      )
                      handleComplete(data.output)
                    } else {
                      console.error('Failed to fetch output from API:', data)
                    }
                  })
                  .catch(err => {
                    console.error('Error fetching output from API:', err)
                  })
              }
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
          }
        }

        wsRef.current.onerror = (event: Event) => {
          if (isCleanedUp || !mountedRef.current) return

          wsConnectAttempts++
          console.error('WebSocket error (attempt ' + wsConnectAttempts + '):', event)

          // If WebSocket fails after max attempts, fall back to polling
          if (wsConnectAttempts >= maxWsAttempts) {
            console.warn('WebSocket failed. Falling back to polling...')
            setWsConnected(false)
            startPolling()
          }
        }

        wsRef.current.onclose = (event) => {
          if (isCleanedUp) return

          console.log('WebSocket closed:', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
          })
          setWsConnected(false)

          // Don't reconnect if session is completed or component is unmounted
          if (completedSessions.has(sessionId) || !mountedRef.current) {
            return
          }
        }

        wsRef.current.onopen = () => {
          if (isCleanedUp || !mountedRef.current) return

          console.log('WebSocket connected successfully')
          setWsConnected(true)
          wsConnectAttempts = 0 // Reset counter on successful connection
        }
      } catch (error) {
        if (isCleanedUp || !mountedRef.current) return

        console.error('Failed to create WebSocket:', error)
        wsConnectAttempts++
        if (wsConnectAttempts >= maxWsAttempts) {
          console.warn('WebSocket creation failed. Using polling as fallback...')
          startPolling()
        }
      }
    }

    const startPolling = () => {
      if (isCleanedUp || !mountedRef.current || pollingIntervalRef.current) return

      console.log('Starting polling for session:', sessionId)
      const apiUrl = typeof window !== 'undefined' && process.env.NEXT_PUBLIC_API_URL
        ? process.env.NEXT_PUBLIC_API_URL
        : 'http://127.0.0.1:8000/api'

      pollingIntervalRef.current = setInterval(async () => {
        if (isCleanedUp || !mountedRef.current || completedSessions.has(sessionId)) {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
          return
        }

        try {
          const response = await fetch(`${apiUrl}/council/orchestrate/${sessionId}`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          })

          if (!response.ok) {
            console.warn(`Polling returned status ${response.status}`)
            return
          }

          const data = await response.json()
          console.log('Polling update:', data)

          if (data.status === 'success' && data.output) {
            setAgents((prev) =>
              prev.map((agent) =>
                agent.name === 'Final Answer'
                  ? { ...agent, status: 'complete', output: data.output }
                  : agent
              )
            )
            handleComplete(data.output)
          } else if (data.status === 'error') {
            console.error('Orchestration error:', data.error)
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current)
              pollingIntervalRef.current = null
            }
          }
        } catch (error) {
          console.error('Polling error:', error)
        }
      }, 2000) // Poll every 2 seconds (reduced frequency to prevent overload)
    }

    // Add a small delay before connecting to allow React to stabilize
    const connectionTimer = setTimeout(() => {
      if (!isCleanedUp && mountedRef.current) {
        connectWebSocket()
      }
    }, 100)

    return () => {
      isCleanedUp = true
      mountedRef.current = false
      clearTimeout(connectionTimer)

      // Only close WebSocket if session is completed or component is truly unmounting
      // Don't close if this is just a dependency change re-run
      if (wsRef.current && completedSessions.has(sessionId)) {
        try {
          wsRef.current.close(1000, 'Session completed')
        } catch (e) {
          // Ignore close errors
        }
        wsRef.current = null
      }

      // Reset connection attempted flag so reconnection is possible
      // This handles the case where effect re-runs due to dependency changes
      connectionAttemptedRef.current = false

      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }, [sessionId, isSessionCompleted, handleComplete])

  // Update execution time and running agent durations
  useEffect(() => {
    const timer = setInterval(() => {
      const totalTime = Math.floor((Date.now() - startTimeRef.current) / 1000)
      setExecutionTime(totalTime)

      // Update duration for running agents
      setAgents((prev) =>
        prev.map((agent) => {
          if (agent.status === 'running') {
            // Find when this agent started (estimate based on other agents)
            const agentStartTime = agent.startTime || startTimeRef.current
            const duration = Math.floor((Date.now() - agentStartTime) / 1000)
            return { ...agent, duration: Math.max(duration, agent.duration) }
          }
          return agent
        })
      )
    }, 100) // Update more frequently for smoother duration display

    return () => clearInterval(timer)
  }, [])

  return (
    <div className="w-full space-y-3">
      {/* Collapsible Header */}
      <div
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="cursor-pointer flex items-center justify-between p-3 rounded-lg bg-gradient-to-r from-blue-500/10 to-blue-500/5 hover:from-blue-500/15 hover:to-blue-500/10 border border-blue-500/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 text-blue-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-blue-400" />
          )}
          <Zap className="w-4 h-4 text-blue-400" />
          <span className="font-semibold text-white">Council Orchestration</span>
        </div>
        <span className="text-sm text-blue-300 font-mono">{executionTime}s total</span>
      </div>

      {/* Orchestration Details - Vertical List Layout */}
      {!isCollapsed && (
        <div className="space-y-2 pl-0">
          {/* Split View: Agent List + Output */}
          <div className="grid grid-cols-5 gap-4">
            {/* Left: Agent List */}
            <div className="col-span-2 space-y-2 max-h-[600px] overflow-y-auto pr-2">
              {agents.map((agent, index) => (
                <div
                  key={agent.name}
                  onClick={() => setSelectedAgent(agent.name)}
                  className={cn(
                    'p-3 rounded-lg border-l-4 cursor-pointer transition-all flex items-center justify-between group',
                    selectedAgent === agent.name
                      ? 'bg-blue-500/15 border-l-blue-500 border border-blue-500/30'
                      : 'bg-zinc-900/30 border-l-zinc-700 border border-zinc-800/50 hover:bg-zinc-900/50 hover:border-zinc-700/50',
                    {
                      'opacity-60': agent.status === 'pending',
                    }
                  )}
                >
                  <div className="flex items-center gap-3 flex-1">
                    {/* Status Indicator */}
                    <div className="flex-shrink-0">
                      {agent.status === 'pending' && (
                        <div className="w-2 h-2 rounded-full bg-zinc-400" />
                      )}
                      {agent.status === 'running' && (
                        <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
                      )}
                      {agent.status === 'complete' && (
                        <div className="w-2 h-2 rounded-full bg-green-400" />
                      )}
                    </div>

                    {/* Agent Info */}
                    <div className="flex-1">
                      <div className="text-sm font-medium text-white">{agent.name}</div>
                      <div className="text-xs text-zinc-400 mt-0.5">
                        {agent.status === 'pending' && 'Pending'}
                        {agent.status === 'running' && 'Running...'}
                        {agent.status === 'complete' && 'Complete'}
                      </div>
                    </div>
                  </div>

                  {/* Duration Badge */}
                  <div className="ml-4 text-right flex-shrink-0">
                    {agent.duration > 0 && (
                      <div className="text-xs font-mono text-blue-300 group-hover:text-blue-200 transition-colors">
                        {agent.duration}s
                      </div>
                    )}
                    {agent.status === 'running' && (
                      <div className="text-xs text-yellow-300 font-mono">
                        ...
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Right: Selected Agent Output - Expanded for Judge Agent */}
            <div className={cn(
              "overflow-hidden",
              selectedAgent === "Judge Agent"
                ? "col-span-3 max-h-[600px]"
                : "col-span-3 max-h-[600px]"
            )}>
              {selectedAgent ? (
                <div className="p-6 rounded-lg bg-zinc-900/50 border border-zinc-700/50 h-full flex flex-col">
                  <div className="flex items-center justify-between mb-4">
                    <div className="text-sm font-semibold text-blue-300 uppercase tracking-wide">
                      {selectedAgent}
                    </div>
                    {agents.find((a) => a.name === selectedAgent)?.status === 'running' && (
                      <div className="flex items-center gap-2 text-yellow-400 text-xs">
                        <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
                        Processing...
                      </div>
                    )}
                  </div>
                  <div className="flex-1 overflow-y-auto text-sm text-zinc-300 leading-relaxed space-y-2 font-mono bg-zinc-950/50 p-4 rounded border border-zinc-800/50">
                    {agents.find((a) => a.name === selectedAgent)?.output ? (
                      <div className="whitespace-pre-wrap break-words">
                        {agents.find((a) => a.name === selectedAgent)?.output}
                      </div>
                    ) : (
                      <div className="text-zinc-500 italic flex items-center justify-center h-full">
                        <div className="text-center">
                          {agents.find((a) => a.name === selectedAgent)?.status === 'pending'
                            ? '⊙ Waiting to execute...'
                            : agents.find((a) => a.name === selectedAgent)?.status === 'running'
                              ? (
                                <div className="flex flex-col items-center gap-2">
                                  <div className="w-8 h-8 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin" />
                                  <span>Processing output...</span>
                                </div>
                              )
                              : '● No output available'}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-700/50 border-dashed h-full flex items-center justify-center">
                  <div className="text-xs text-zinc-500 text-center">
                    <div className="mb-2">👆</div>
                    Click an agent to view output
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Final Answer - Rendered like a normal assistant message */}
      {finalAnswer && (
        <div className="mt-4 text-zinc-100 leading-relaxed">
          <CollaborationAttribution
            contributions={agents
              .filter(a => a.status === 'complete' && a.output && a.name !== 'Final Answer')
              .map(a => ({
                model: 'GPT-4o', // Default to GPT-4o as we don't have model info in AgentOutput yet
                role: a.name.replace(' Agent', '').toLowerCase(),
                provider: 'openai'
              }))}
          />
          <EnhancedMessageContent
            content={finalAnswer}
            role="assistant"
          />
          <ResponseMetrics
            durationMs={executionTime * 1000}
            modelsUsed={agents.filter(a => a.status === 'complete').length}
            stagesCompleted={agents.filter(a => a.status === 'complete').length}
          />
        </div>
      )}
    </div>
  )
}
