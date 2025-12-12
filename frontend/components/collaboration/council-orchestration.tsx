'use client'

import { useState, useEffect, useRef } from 'react'
import { ChevronDown, Eye, Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'

type Phase = 'phase_1' | 'phase_2' | 'phase_3' | 'complete'
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
  duration: number // in seconds
  output?: string
  status: 'pending' | 'running' | 'complete'
  phase: 'phase_1' | 'phase_2' | 'phase_3' | 'final'
}

interface CouncilOrchestrationProps {
  query: string
  orgId: string
  onComplete: (output: string) => void
  onClose: () => void
}

export function CouncilOrchestration({
  query,
  orgId,
  onComplete,
  onClose,
}: CouncilOrchestrationProps) {
  const [agents, setAgents] = useState<AgentOutput[]>([
    { name: 'Optimizer Agent', duration: 0, status: 'pending', phase: 'phase_1' },
    { name: 'Red Teamer Agent', duration: 0, status: 'pending', phase: 'phase_1' },
    { name: 'Data Engineer Agent', duration: 0, status: 'pending', phase: 'phase_1' },
    { name: 'Researcher Agent', duration: 0, status: 'pending', phase: 'phase_1' },
    { name: 'Architect Agent', duration: 0, status: 'pending', phase: 'phase_1' },
    { name: 'Debate Synthesizer', duration: 0, status: 'pending', phase: 'phase_2' },
    { name: 'Judge Agent', duration: 0, status: 'pending', phase: 'phase_3' },
    { name: 'Final Answer', duration: 0, status: 'pending', phase: 'final' },
  ])

  const [selectedAgent, setSelectedAgent] = useState<AgentName>('Optimizer Agent')
  const [currentPhase, setCurrentPhase] = useState<Phase>('phase_1')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [executionTime, setExecutionTime] = useState<number>(0)
  const [showProcess, setShowProcess] = useState(false)
  const [finalAnswer, setFinalAnswer] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const startTimeRef = useRef<number>(Date.now())

  // Start council execution
  useEffect(() => {
    const startCouncil = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api'
        console.log('Starting council with API URL:', apiUrl)

        const response = await fetch(`${apiUrl}/council/orchestrate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-org-id': orgId,
          },
          body: JSON.stringify({
            query,
            output_mode: 'deliverable-ownership',
          }),
        })

        console.log('Response status:', response.status)

        if (!response.ok) {
          const errorText = await response.text()
          console.error('API Error:', response.status, errorText)
          throw new Error(`API Error: ${response.status} - ${errorText}`)
        }

        const data = await response.json()
        console.log('Session created:', data.session_id)
        setSessionId(data.session_id)

        // Connect WebSocket
        connectWebSocket(data.session_id)
      } catch (error) {
        console.error('Failed to start council:', error)
      }
    }

    startCouncil()
  }, [query, orgId])

  // Update execution time
  useEffect(() => {
    const timer = setInterval(() => {
      setExecutionTime(Math.floor((Date.now() - startTimeRef.current) / 1000))
    }, 100)

    return () => clearInterval(timer)
  }, [])

  // Connect to WebSocket
  const connectWebSocket = (id: string) => {
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${typeof window !== 'undefined' ? window.location.host : 'localhost:8000'}/api/council/ws/${id}`

    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onmessage = (event) => {
      const message = JSON.parse(event.data)

      if (message.type === 'progress') {
        handleProgress(message.current_phase)
      } else if (message.type === 'complete') {
        handleComplete(message)
      }
    }

    wsRef.current.onerror = () => {
      console.error('WebSocket error')
    }
  }

  const handleProgress = (phase: string) => {
    // Map phase messages to agent updates
    if (phase?.includes('Optimizer')) {
      updateAgent('Optimizer Agent', 'running')
      setCurrentPhase('phase_1')
    } else if (phase?.includes('Red Teamer')) {
      updateAgent('Red Teamer Agent', 'running')
      setCurrentPhase('phase_1')
    } else if (phase?.includes('Data Engineer')) {
      updateAgent('Data Engineer Agent', 'running')
      setCurrentPhase('phase_1')
    } else if (phase?.includes('Researcher')) {
      updateAgent('Researcher Agent', 'running')
      setCurrentPhase('phase_1')
    } else if (phase?.includes('Architect')) {
      updateAgent('Architect Agent', 'running')
      setCurrentPhase('phase_1')
    } else if (phase?.includes('Synthesizer')) {
      // Mark phase 1 complete
      setAgents((prev) =>
        prev.map((a) =>
          a.phase === 'phase_1' ? { ...a, status: 'complete' } : a
        )
      )
      updateAgent('Debate Synthesizer', 'running')
      setCurrentPhase('phase_2')
    } else if (phase?.includes('Judge')) {
      // Mark phase 2 complete
      setAgents((prev) =>
        prev.map((a) =>
          a.phase === 'phase_2' ? { ...a, status: 'complete' } : a
        )
      )
      updateAgent('Judge Agent', 'running')
      setCurrentPhase('phase_3')
    }
  }

  const handleComplete = (message: any) => {
    setAgents((prev) =>
      prev.map((a) =>
        a.phase === 'phase_3' ? { ...a, status: 'complete' } : a
      )
    )
    updateAgent('Final Answer', 'complete')
    setCurrentPhase('complete')
    setFinalAnswer(message.output)
    onComplete(message.output)
  }

  const updateAgent = (name: AgentName, status: 'running' | 'complete') => {
    setAgents((prev) =>
      prev.map((a) =>
        a.name === name
          ? {
              ...a,
              status,
              duration: status === 'complete' ? executionTime : a.duration,
            }
          : a
      )
    )
  }

  const selectedAgentData = agents.find((a) => a.name === selectedAgent)

  return (
    <div className="flex h-full gap-4 p-4 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 rounded-lg">
      {/* Left Panel - Phase List */}
      <div className="flex-shrink-0 w-80">
        <div className="space-y-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                Council Orchestration
              </h3>
            </div>
            <span className="text-sm text-slate-600 dark:text-slate-400">
              {executionTime}s
            </span>
          </div>

          {/* Agent List */}
          <div className="space-y-1 max-h-96 overflow-y-auto">
            {agents.map((agent, idx) => (
              <AgentListItem
                key={agent.name}
                agent={agent}
                isSelected={selectedAgent === agent.name}
                onSelect={() => setSelectedAgent(agent.name)}
                isLastInPhase={
                  idx === agents.findIndex((a) => a.phase !== agent.phase) - 1
                }
              />
            ))}
          </div>

          {/* Show Process Toggle */}
          <button
            onClick={() => setShowProcess(!showProcess)}
            className={cn(
              'mt-4 w-full flex items-center gap-2 px-3 py-2 rounded-lg',
              'text-sm font-medium transition-colors',
              'bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600',
              'text-slate-900 dark:text-slate-100'
            )}
          >
            <Eye className="w-4 h-4" />
            Show Process
            <ChevronDown
              className={cn(
                'w-4 h-4 ml-auto transition-transform',
                showProcess && 'rotate-180'
              )}
            />
          </button>
        </div>
      </div>

      {/* Right Panel - Output Display */}
      <div className="flex-1 min-w-0">
        {!finalAnswer ? (
          <div className="h-full rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-4 flex flex-col">
            {/* Agent Output */}
            <div className="flex-1 overflow-y-auto">
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  {selectedAgent}
                </h4>
                <div className="text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/50 rounded p-3">
                  {selectedAgentData?.status === 'running' && (
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                      <span>Running...</span>
                    </div>
                  )}
                  {selectedAgentData?.status === 'complete' && selectedAgentData.output && (
                    <div className="whitespace-pre-wrap font-mono text-xs">
                      {selectedAgentData.output.substring(0, 500)}...
                    </div>
                  )}
                  {selectedAgentData?.status === 'pending' && (
                    <span className="text-slate-500 dark:text-slate-500">
                      Waiting to start...
                    </span>
                  )}
                </div>
              </div>

              {/* Timing Info */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-50 dark:bg-slate-900/50 rounded p-2">
                  <p className="text-slate-600 dark:text-slate-400">Duration</p>
                  <p className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                    {selectedAgentData?.duration.toFixed(1)}s
                  </p>
                </div>
                <div className="bg-slate-50 dark:bg-slate-900/50 rounded p-2">
                  <p className="text-slate-600 dark:text-slate-400">Status</p>
                  <p className="font-semibold text-slate-900 dark:text-slate-100 capitalize">
                    {selectedAgentData?.status}
                  </p>
                </div>
              </div>
            </div>

            {/* Phase Indicator */}
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                <span>Current Phase:</span>
                <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                  {currentPhase === 'phase_1' && '1 of 3 - Parallel Agents'}
                  {currentPhase === 'phase_2' && '2 of 3 - Synthesizer'}
                  {currentPhase === 'phase_3' && '3 of 3 - Judge'}
                  {currentPhase === 'complete' && 'Complete'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <FinalAnswerDisplay answer={finalAnswer} onClose={onClose} />
        )}
      </div>

      {/* Expanded Process Panel */}
      {showProcess && (
        <ProcessPanel agents={agents} />
      )}
    </div>
  )
}

interface AgentListItemProps {
  agent: AgentOutput
  isSelected: boolean
  onSelect: () => void
  isLastInPhase: boolean
}

function AgentListItem({
  agent,
  isSelected,
  onSelect,
  isLastInPhase,
}: AgentListItemProps) {
  return (
    <div>
      <button
        onClick={onSelect}
        className={cn(
          'w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all',
          isSelected
            ? 'bg-blue-100 dark:bg-blue-900/30 border border-blue-300 dark:border-blue-700'
            : 'hover:bg-slate-200 dark:hover:bg-slate-700'
        )}
      >
        {/* Status Indicator */}
        <div className="flex-shrink-0">
          {agent.status === 'pending' && (
            <div className="w-3 h-3 rounded-full bg-slate-300 dark:bg-slate-600" />
          )}
          {agent.status === 'running' && (
            <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
          )}
          {agent.status === 'complete' && (
            <div className="w-3 h-3 rounded-full bg-green-600" />
          )}
        </div>

        {/* Agent Name */}
        <span className="flex-1 text-left text-sm font-medium text-slate-900 dark:text-slate-100">
          {agent.name}
        </span>

        {/* Duration */}
        <span className="text-xs text-slate-600 dark:text-slate-400">
          {agent.duration > 0 ? `${agent.duration.toFixed(1)}s` : '—'}
        </span>
      </button>

      {/* Phase Divider */}
      {isLastInPhase && (
        <div className="my-2 border-t-2 border-dashed border-slate-300 dark:border-slate-600" />
      )}
    </div>
  )
}

interface FinalAnswerDisplayProps {
  answer: string
  onClose: () => void
}

function FinalAnswerDisplay({ answer, onClose }: FinalAnswerDisplayProps) {
  const [copied, setCopied] = useState(false)

  const copyToClipboard = () => {
    navigator.clipboard.writeText(answer)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="h-full rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-4 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          Final Answer
        </h4>
        <button
          onClick={copyToClipboard}
          className={cn(
            'flex items-center gap-1 px-2 py-1 rounded text-xs',
            'transition-colors',
            copied
              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
              : 'bg-slate-100 dark:bg-slate-900/50 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800'
          )}
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" />
              Copied
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              Copy
            </>
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto bg-slate-50 dark:bg-slate-900/50 rounded p-3">
        <div className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300 font-mono leading-relaxed">
          {answer}
        </div>
      </div>

      <button
        onClick={onClose}
        className={cn(
          'mt-4 w-full py-2 rounded-lg font-medium text-sm',
          'bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600',
          'text-white transition-colors'
        )}
      >
        Close & Return to Chat
      </button>
    </div>
  )
}

interface ProcessPanelProps {
  agents: AgentOutput[]
}

function ProcessPanel({ agents }: ProcessPanelProps) {
  const [expandedAgent, setExpandedAgent] = useState<AgentName | null>(null)

  return (
    <div className="flex-shrink-0 w-72 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-4 overflow-y-auto max-h-96">
      <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">
        Execution Details
      </h4>

      <div className="space-y-2">
        {agents.map((agent) => (
          <div
            key={agent.name}
            className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden"
          >
            <button
              onClick={() =>
                setExpandedAgent(
                  expandedAgent === agent.name ? null : agent.name
                )
              }
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
            >
              <ChevronDown
                className={cn(
                  'w-4 h-4 flex-shrink-0 transition-transform',
                  expandedAgent === agent.name && 'rotate-180'
                )}
              />
              <span className="text-sm font-medium text-slate-900 dark:text-slate-100 flex-1 text-left">
                {agent.name}
              </span>
              <span className="text-xs text-slate-600 dark:text-slate-400">
                {agent.duration.toFixed(1)}s
              </span>
            </button>

            {expandedAgent === agent.name && agent.output && (
              <div className="px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-700">
                <div className="text-xs text-slate-700 dark:text-slate-300 max-h-32 overflow-y-auto">
                  {agent.output}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
