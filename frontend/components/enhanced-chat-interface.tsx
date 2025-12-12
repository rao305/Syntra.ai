"use client"

import { CodePanel } from "@/components/code-panel"
import { CollabPanel, type CollabPanelState } from "@/components/collaborate/CollabPanel"
import { CollaborationPipelineDetails } from "@/components/collaborate/CollaborationPipelineDetails"
import { EnhancedMessageContent } from "@/components/enhanced-message-content"
import { ImageInputArea } from "@/components/image-input-area"
import { SimpleLoadingIndicator } from "@/components/simple-loading-indicator"
import { ThinkingStream } from "@/components/thinking-stream"
import type { StageId, StageState, StageStatus } from "@/lib/collabStages"
import { cn } from "@/lib/utils"
import { useWorkflowStore } from "@/store/workflow-store"
import { Bookmark, Brain, Bug, Copy, RefreshCw, Share2 } from "lucide-react"
import Image from "next/image"
import * as React from "react"
import { useState } from "react"

/**
 * Mapping of supported backend model IDs to display names
 * Only models that are actually supported and configured should be shown
 */
const SUPPORTED_MODELS: Record<string, string> = {
  // OpenAI models
  'gpt-4o': 'GPT-4o',
  'gpt-4o-mini': 'GPT-4o Mini',
  'gpt-4': 'GPT-4',
  'gpt-3.5-turbo': 'GPT-3.5 Turbo',

  // Google/Gemini models
  'gemini-2.5-flash': 'Gemini 2.5 Flash',
  'gemini-2.5-pro': 'Gemini 2.5 Pro',
  'gemini-2.0-flash': 'Gemini 2.0 Flash',
  'gemini-pro': 'Gemini Pro',
  'gemini-flash': 'Gemini Flash',

  // Perplexity models
  'perplexity-sonar': 'Perplexity Sonar',
  'perplexity-sonar-pro': 'Perplexity Sonar Pro',
  'sonar': 'Perplexity Sonar',
  'sonar-pro': 'Perplexity Sonar Pro',

  // Kimi/Moonshot models
  'kimi-k2-turbo': 'Kimi K2 Turbo',
  'kimi-k2-turbo-preview': 'Kimi K2 Turbo',
  'moonshot-v1-8k': 'Moonshot v1 8K',
  'moonshot-v1-32k': 'Moonshot v1 32K',
  'moonshot-v1-128k': 'Moonshot v1 128K',

  // OpenRouter models
  'openrouter-default': 'OpenRouter Mix',
  'google/gemini-flash-1.5-8b:free': 'Gemini Flash 8B',

  // Legacy/fallback names
  'gpt': 'GPT-4',
  'gemini': 'Gemini',
  'perplexity': 'Perplexity',
  'kimi': 'Kimi',
}

/**
 * Get display name for a model, only if it's supported
 */
function getSupportedModelDisplayName(modelName: string | undefined | null): string | null {
  if (!modelName || modelName === 'undefined' || modelName === 'null' || modelName === 'DAC' || modelName === 'auto') {
    return null
  }

  // Check exact match first
  if (SUPPORTED_MODELS[modelName]) {
    return SUPPORTED_MODELS[modelName]
  }

  // Check case-insensitive match
  const lowerModelName = modelName.toLowerCase()
  for (const [key, displayName] of Object.entries(SUPPORTED_MODELS)) {
    if (key.toLowerCase() === lowerModelName) {
      return displayName
    }
  }

  // Check if it contains a supported model identifier
  for (const [key, displayName] of Object.entries(SUPPORTED_MODELS)) {
    if (lowerModelName.includes(key.toLowerCase()) || key.toLowerCase().includes(lowerModelName)) {
      return displayName
    }
  }

  // If not found in supported models, return null (don't display)
  return null
}

interface ImageFile {
  file?: File
  url: string
  id: string
}

interface CollaborationStage {
  id: string
  label: string
  status: "pending" | "active" | "done"
}

interface PipelineStage {
  id: string
  role: string
  label: string
  model?: string
  modelName?: string
  output?: string
  status: "pending" | "active" | "done" | "failed"
  latency_ms?: number
  tokens?: { input?: number; output?: number }
}

interface Review {
  id: string
  source: string
  model?: string
  modelName?: string
  stance: "agree" | "disagree" | "mixed" | "unknown"
  feedback?: string
  issues?: string[]
  suggestions?: string[]
  content?: string
}

interface CollaborationState {
  mode: "thinking" | "streaming_final" | "complete"
  stages: CollaborationStage[]
  currentStageId?: string
  // Detailed pipeline data for transparency
  pipelineStages?: PipelineStage[]
  reviews?: Review[]
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  images?: ImageFile[]
  chainOfThought?: string
  timestamp?: string
  modelId?: string
  modelName?: string
  reasoningType?: 'coding' | 'analysis' | 'creative' | 'research' | 'conversation'
  confidence?: number
  processingTime?: number
  // Collaboration state for live thinking bubbles
  collaboration?: CollaborationState
}

interface ChatInterfaceProps {
  messages: Message[]
  onSendMessage: (content: string, images?: ImageFile[]) => void
  onUpdateMessage?: (messageId: string, updates: Partial<Message>) => void
  isLoading?: boolean
  selectedModel: string
  onModelSelect: (modelId: string) => void
  onContinueWorkflow?: () => void
  autoRoutedModel?: string | null
  collabPanel?: CollabPanelState
}

export function EnhancedChatInterface({
  messages,
  onSendMessage,
  onUpdateMessage,
  isLoading = false,
  selectedModel,
  onModelSelect,
  onContinueWorkflow,
  autoRoutedModel,
  collabPanel
}: ChatInterfaceProps) {
  const [expandedThoughts, setExpandedThoughts] = useState<Set<string>>(new Set())
  const [codePanelOpen, setCodePanelOpen] = useState(false)
  const [codePanelContent, setCodePanelContent] = useState({ code: '', language: '', title: '' })
  const { isCollaborateMode, steps = [], updateStep, mode: storeMode, setMode: setStoreMode } = useWorkflowStore()

  // Multi-Agent Thinking UI State - use store mode as source of truth
  const thinkingMode = storeMode
  const [showThinkingUI, setShowThinkingUI] = useState(false)
  const [currentStepIndex, setCurrentStepIndex] = useState(0)

  // Handle mode change - update store mode (which will update all steps)
  const handleModeChange = (newMode: "auto" | "manual") => {
    console.log(`🔄 Changing workflow mode to: ${newMode}`)

    // Update the store mode (this will automatically update all pending/running/awaiting_user steps)
    setStoreMode(newMode)

    // Get updated steps after mode change
    const { steps: updatedSteps = [] } = useWorkflowStore.getState()

    // If switching to auto mode and any step is awaiting_user, auto-approve it
    if (newMode === "auto") {
      updatedSteps.forEach(step => {
        if (step.status === "awaiting_user") {
          console.log(`🚀 Auto-approving step ${step.id} (${step.role}) since mode changed to auto`)
          updateStep(step.id, {
            status: "done",
            outputFinal: step.outputDraft || step.outputFinal
          })
        }
      })

      // Continue workflow after a short delay if there were steps to approve
      const hasApprovedSteps = updatedSteps.some(s => s.status === "awaiting_user")
      if (hasApprovedSteps && onContinueWorkflow) {
        setTimeout(() => {
          console.log('🔄 Auto-continuing workflow after mode change...')
          onContinueWorkflow()
        }, 100)
      }
    }
  }

  // Convert workflow steps to agent steps format
  const agentSteps = (steps || []).map((step, index) => {
    // Map workflow status to agent status
    let agentStatus: "waiting" | "thinking" | "awaiting_approval" | "done" | "rerun" | "skipped" | "error" = "waiting"
    switch (step.status) {
      case "pending": agentStatus = "waiting"; break
      case "running": agentStatus = "thinking"; break
      case "awaiting_user": agentStatus = "awaiting_approval"; break
      case "done": agentStatus = "done"; break
      case "error": agentStatus = "error"; break
      case "cancelled": agentStatus = "skipped"; break
    }

    // Get model name
    const modelName = step.model === "gpt" ? "GPT" :
      step.model === "gemini" ? "Gemini" :
        step.model === "perplexity" ? "Perplexity" :
          step.model === "kimi" ? "Kimi" : step.model

    return {
      id: step.id,
      role: step.role as "analyst" | "researcher" | "creator" | "critic" | "synthesizer",
      name: `${step.role.charAt(0).toUpperCase() + step.role.slice(1)} (${modelName})`,
      icon: Brain, // Will be handled by getAgentIcon in the component
      status: agentStatus,
      output: step.outputFinal || step.outputDraft, // Show draft if final not available
      summary: step.outputDraft ? step.outputDraft.substring(0, 150) + "..." : undefined,
      context: [modelName, ...(step.metadata?.providerName ? [step.metadata.providerName] : [])],
      error: step.error?.message
    }
  })

  // Convert workflow steps to collaboration stages format for timeline
  const collaborationStages: StageState[] = (steps || []).map((step) => {
    let stageStatus: StageStatus = "idle"
    switch (step.status) {
      case "pending": stageStatus = "idle"; break
      case "running": stageStatus = "running"; break
      case "awaiting_user": stageStatus = "running"; break
      case "done": stageStatus = "done"; break
      case "error": stageStatus = "error"; break
      case "cancelled": stageStatus = "error"; break
    }

    const modelName = step.model === "gpt" ? "GPT" :
      step.model === "gemini" ? "Gemini" :
        step.model === "perplexity" ? "Perplexity" :
          step.model === "kimi" ? "Kimi" : step.model

    return {
      id: step.role as StageId,
      label: step.role.charAt(0).toUpperCase() + step.role.slice(1),
      modelName,
      status: stageStatus,
    }
  })

  // Update current step index based on workflow progress
  React.useEffect(() => {
    // Priority 1: Find step awaiting approval (most important for manual mode)
    const awaitingIndex = steps.findIndex(s => s.status === "awaiting_user")
    if (awaitingIndex !== -1) {
      setCurrentStepIndex(awaitingIndex)
      console.log(`📍 Setting currentStepIndex to ${awaitingIndex} (step awaiting approval: ${steps[awaitingIndex].id})`)
      return
    }

    // Priority 2: Find step that's currently running
    const runningIndex = steps.findIndex(s => s.status === "running")
    if (runningIndex !== -1) {
      setCurrentStepIndex(runningIndex)
      return
    }

    // Priority 3: Find the last completed step and point to next
    const lastCompletedIndex = steps.map((s, i) => s.status === "done" ? i : -1).filter(i => i !== -1).pop()
    if (lastCompletedIndex !== undefined) {
      const nextIndex = Math.min(lastCompletedIndex + 1, steps.length - 1)
      setCurrentStepIndex(nextIndex)
    }
  }, [steps])

  const toggleThought = (messageId: string) => {
    const newExpanded = new Set(expandedThoughts)
    if (newExpanded.has(messageId)) {
      newExpanded.delete(messageId)
    } else {
      newExpanded.add(messageId)
    }
    setExpandedThoughts(newExpanded)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const handleCodePanelOpen = (code: string, language: string, title?: string) => {
    setCodePanelContent({
      code,
      language,
      title: title || `${language.toUpperCase()} Code`
    })
    setCodePanelOpen(true)
  }

  const getReasoningTypeColor = (type?: string) => {
    switch (type) {
      case 'coding': return 'text-blue-400'
      case 'analysis': return 'text-green-400'
      case 'creative': return 'text-purple-400'
      case 'research': return 'text-yellow-400'
      default: return 'text-zinc-400'
    }
  }

  const getReasoningTypeIcon = (type?: string) => {
    switch (type) {
      case 'coding': return '💻'
      case 'analysis': return '🔍'
      case 'creative': return '🎨'
      case 'research': return '📚'
      default: return '💭'
    }
  }

  // Multi-Agent Thinking Handlers
  const handleApproveStep = (stepId: string) => {
    console.log('✅ Approving step:', stepId)
    // Update step status to done and continue workflow
    const step = steps.find(s => s.id === stepId)
    if (step && step.status === "awaiting_user") {
      // Update step to done and continue workflow
      updateStep(stepId, {
        status: "done",
        outputFinal: step.outputDraft || step.outputFinal
      })

      console.log(`✅ Step ${stepId} approved and set to done, continuing workflow...`)

      // Use setTimeout to ensure state update propagates before continuing
      setTimeout(() => {
        // Continue workflow execution
        if (onContinueWorkflow) {
          console.log('🔄 Calling onContinueWorkflow...')
          onContinueWorkflow()
        }
      }, 100)
    } else {
      console.warn(`⚠️ Cannot approve step ${stepId}: step not found or status is not awaiting_user (status: ${step?.status})`)
    }

    // Move to next step in UI
    const stepIndex = agentSteps.findIndex(s => s.id === stepId)
    if (stepIndex !== -1 && stepIndex < agentSteps.length - 1) {
      setCurrentStepIndex(stepIndex + 1)
    }
  }

  const handleEditStep = (stepId: string, newOutput: string) => {
    console.log('Editing step:', stepId, newOutput)
    // Update the step output
  }

  const handleRerunStep = (stepId: string) => {
    console.log('Rerunning step:', stepId)
    // Trigger rerun for specific step
  }

  const handleSkipStep = (stepId: string) => {
    console.log('Skipping step:', stepId)
    // Skip step and move to next
    const stepIndex = agentSteps.findIndex(s => s.id === stepId)
    if (stepIndex !== -1 && stepIndex < agentSteps.length - 1) {
      setCurrentStepIndex(stepIndex + 1)
    }
  }

  const handleStopRun = () => {
    console.log('Stopping collaboration run')
    setShowThinkingUI(false)
  }

  const handleRerunAll = () => {
    console.log('Rerunning all steps')
    setCurrentStepIndex(0)
  }

  // Show thinking UI only when a workflow is actually running (has active steps)
  // Don't show it just because collaborate mode is enabled - let user see Auto/Manual toggle first
  React.useEffect(() => {
    if (!isCollaborateMode) {
      setShowThinkingUI(false)
      return
    }

    // Check if the workflow has actually started
    // Workflow has started if any step has a status other than "pending" or has output
    const workflowHasStarted = agentSteps.some(s =>
      s.status !== "waiting" || s.output !== undefined
    )

    // Don't show UI if workflow hasn't started yet
    // This allows user to see Auto/Manual toggle and send a message first
    if (!workflowHasStarted) {
      setShowThinkingUI(false)
      return
    }

    // Check if all steps are completed (especially synthesizer)
    const allStepsDone = agentSteps.every(s => s.status === "done" || s.status === "error" || s.status === "skipped")
    const synthesizerDone = agentSteps.find(s => s.role === "synthesizer")?.status === "done"

    // Hide modal if synthesizer is done (workflow complete)
    if (allStepsDone && synthesizerDone) {
      setShowThinkingUI(false)
      return
    }

    // Show UI if there are any active steps (running, awaiting_approval) or if workflow is in progress
    const hasActiveSteps = agentSteps.some(s => s.status === "thinking" || s.status === "awaiting_approval")
    const hasPendingSteps = agentSteps.some(s => s.status === "waiting")

    // Always show UI if there are steps awaiting approval, thinking, or pending
    // IMPORTANT: Keep UI visible if any step is awaiting approval, even if isLoading is false
    if (hasActiveSteps || hasPendingSteps || isLoading) {
      setShowThinkingUI(true)

      // Update currentStepIndex to point to the step that needs attention
      const awaitingStepIndex = agentSteps.findIndex(s => s.status === "awaiting_approval")
      if (awaitingStepIndex !== -1) {
        setCurrentStepIndex(awaitingStepIndex)
        console.log(`📍 Updated currentStepIndex to ${awaitingStepIndex} (step: ${agentSteps[awaitingStepIndex].id}) - showing approval UI`)
      } else {
        // If no step is awaiting approval, find the first thinking or waiting step
        const activeStepIndex = agentSteps.findIndex(s => s.status === "thinking" || s.status === "waiting")
        if (activeStepIndex !== -1) {
          setCurrentStepIndex(activeStepIndex)
        }
      }
    } else {
      // Only hide UI if there are truly no active steps AND not loading AND not in manual mode with awaiting steps
      // Double-check for awaiting_user status in raw steps (before conversion to agentSteps)
      const hasAwaitingUser = steps.some(s => s.status === "awaiting_user")
      if (!hasAwaitingUser) {
        console.log(`🔒 Hiding thinking UI - no active steps and no awaiting approval`)
        setShowThinkingUI(false)
      } else {
        console.log(`🔓 Keeping thinking UI visible - found steps awaiting approval`)
        setShowThinkingUI(true)
      }
    }
  }, [isCollaborateMode, agentSteps, isLoading, steps])

  return (
    <div className="flex-1 flex flex-col h-full relative">
      <div className="flex-1 overflow-y-auto p-4 pb-40">
        <div className="max-w-4xl mx-auto pt-8 pb-40 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-[50vh] text-center space-y-4">
              <Image
                src="/syntralogo.png"
                alt="Syntra Logo"
                width={120}
                height={120}
                className="mb-4"
              />
              <h2 className="text-2xl font-semibold text-white">
                Your Multi-Agent Workspace Starts Here.
              </h2>
              <p className="text-white/80 max-w-lg">
                I'm powered by a network of specialized models. Ask anything — I'll gather the right experts and reason step-by-step.
              </p>
            </div>
          )}

          {collabPanel && <CollabPanel state={collabPanel} />}

          {messages.map((message, index) => {
            // Ensure unique key - handle cases where id might be null, undefined, or "None"
            // Always include index to guarantee uniqueness even if IDs are duplicated
            const messageId = message.id && message.id !== 'None' && message.id !== 'null' && String(message.id).trim() !== ''
              ? `${message.id}-${index}`
              : `message-${index}-${message.role}`
            return (
              <div key={messageId} className={cn(
                "space-y-3 transition-all duration-200",
                index > 0 && "pt-6 border-t border-zinc-800/50"
              )}>
                {message.role === 'user' ? (
                  <div className="flex justify-end">
                    <div className="flex flex-col items-end gap-2 max-w-[55%]">
                      <div className="text-xs text-zinc-400 px-1">You</div>
                      <div className="text-white text-[15px] leading-relaxed px-1 break-words">
                        {message.content}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-start">
                    <div className="max-w-[90%]">

                      {/* Message Content */}
                      {message.collaboration && message.collaboration.mode !== "complete" ? (
                        // Show thinking/streaming UI only while collaboration is in progress
                        <div className="px-1">
                          <ThinkingStream
                            stages={message.collaboration.stages}
                            mode={message.collaboration.mode}
                            finalContent={message.content}
                            onViewProcess={() => {
                              // TODO: Open process details modal/panel
                              console.log('View collaboration process for message:', message.id)
                            }}
                          />
                        </div>
                      ) : (
                        // Render final content like normal mode - no boxes or special formatting
                        <div className="text-zinc-100 leading-relaxed px-1 py-2">
                          <EnhancedMessageContent
                            content={message.content}
                            role={message.role}
                            images={message.images}
                            onCodePanelOpen={handleCodePanelOpen}
                          />
                        </div>
                      )}

                      {/* Model Information - Always show for assistant messages */}
                      {message.role === 'assistant' && (() => {
                        const displayName = getSupportedModelDisplayName(message.modelName)
                        // Always show model name - use supported name if available, otherwise use raw modelName
                        const modelToDisplay = displayName || message.modelName || 'Unknown Model'

                        return (
                          <div className="pt-2 text-xs text-zinc-500 space-y-0.5">
                            <div>
                              <span>Model: </span>
                              <span className="text-zinc-400 font-medium">{modelToDisplay}</span>
                              {message.processingTime && (
                                <span className="ml-3 text-zinc-600">• {message.processingTime}ms</span>
                              )}
                            </div>
                          </div>
                        )
                      })()}

                      {/* Collaboration Pipeline Details - Collapsible */}
                      {message.collaboration && message.collaboration.mode === "complete" && (
                        <CollaborationPipelineDetails
                          stages={message.collaboration.pipelineStages}
                          reviews={message.collaboration.reviews}
                        />
                      )}

                      {/* Message Actions */}
                      <div className="flex items-center gap-1 pt-1">
                        <div></div>

                        <div className="flex items-center">
                          <ActionButton
                            icon={Copy}
                            onClick={() => copyToClipboard(message.content)}
                            tooltip="Copy message"
                          />
                          <ActionButton
                            icon={RefreshCw}
                            tooltip="Regenerate"
                          />
                          <ActionButton
                            icon={Share2}
                            tooltip="Share"
                          />
                          <ActionButton
                            icon={Bookmark}
                            tooltip="Bookmark"
                          />
                          <ActionButton
                            icon={Bug}
                            tooltip="Report issue"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          {/* Loading Indicator - Simple loading with expandable prompt */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-[90%] space-y-2 w-full">
                {isCollaborateMode ? (
                  // Use SimpleLoadingIndicator for collaboration mode
                  (() => {
                    const activeStage = collaborationStages.find((s) => s.status === "running")
                    const stageName = activeStage?.label ? `${activeStage.label} in progress…` : "Processing your request…"
                    const modelName = activeStage?.modelName || "Processing"
                    // Get the model output from the running step
                    const runningStep = steps.find((s) => s.status === "running")
                    const modelOutput = runningStep?.outputDraft || runningStep?.outputFinal || ""
                    return (
                      <SimpleLoadingIndicator
                        modelName={modelName}
                        stageName={stageName}
                        modelOutput={modelOutput}
                        isVisible={true}
                      />
                    )
                  })()
                ) : (
                  <SimpleLoadingIndicator
                    modelName={
                      autoRoutedModel
                        ? autoRoutedModel
                        : selectedModel !== 'auto'
                        ? (SYNTRA_MODELS.find(m => m.id === selectedModel)?.name || selectedModel)
                        : "Auto-selecting best model..."
                    }
                    stageName="Processing your request…"
                    modelOutput=""
                    isVisible={true}
                  />
                )}
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Enhanced Input Area */}
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-zinc-950 via-zinc-950/95 to-transparent pt-8 pb-4 border-t border-zinc-800/50">
        <div className="max-w-2xl mx-auto">
          <ImageInputArea
            onSendMessage={onSendMessage}
            selectedModel={selectedModel}
            onModelSelect={onModelSelect}
            isLoading={isLoading}
            autoRoutedModel={autoRoutedModel}
            showActionButtons={messages.length === 0}
          />
          <div className="flex justify-end mt-2">
            <button className="p-2 text-zinc-500 hover:text-zinc-400 transition-colors rounded-full hover:bg-zinc-900">
              <div className="w-5 h-5 rounded-full border border-zinc-600 flex items-center justify-center text-[10px] font-bold">
                ?
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Code Panel */}
      <CodePanel
        isOpen={codePanelOpen}
        onClose={() => setCodePanelOpen(false)}
        code={codePanelContent.code}
        language={codePanelContent.language}
        title={codePanelContent.title}
      />

      {/* Multi-Agent Thinking UI - REPLACED WITH INLINE COLLABORATION */}
      {/* Collaboration now happens inline within chat messages using ThinkingStream component */}
      {/* Keeping this commented for backwards compatibility during migration */}
      {/*
      <MultiAgentThinking
        isVisible={showThinkingUI}
        mode={thinkingMode}
        userPrompt={messages.find(m => m.role === 'user')?.content || "Collaboration request"}
        steps={agentSteps}
        currentStepIndex={currentStepIndex}
        isRunning={isLoading}
        onModeChange={handleModeChange}
        onApprove={handleApproveStep}
        onEdit={handleEditStep}
        onRerun={handleRerunStep}
        onSkip={handleSkipStep}
        onStop={handleStopRun}
        onRerunAll={handleRerunAll}
      />
      */}
    </div >
  )
}

function ActionButton({
  icon: Icon,
  onClick,
  tooltip
}: {
  icon: any,
  onClick?: () => void,
  tooltip?: string
}) {
  return (
    <button
      className="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 rounded-md transition-colors"
      onClick={onClick}
      title={tooltip}
    >
      <Icon className="w-4 h-4" />
    </button>
  )
}
