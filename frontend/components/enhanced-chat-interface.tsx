"use client"

import { CodePanel } from "@/components/code-panel"
import { CollabPanel, type CollabPanelState } from "@/components/collaborate/CollabPanel"
import { EnhancedMessageContent } from "@/components/enhanced-message-content"
import { ImageInputArea } from "@/components/image-input-area"
import { SimpleLoadingIndicator } from "@/components/simple-loading-indicator"
import { ThinkingStream } from "@/components/thinking-stream"
import type { StageId, StageState, StageStatus } from "@/lib/collabStages"
import { cn } from "@/lib/utils"
import { useWorkflowStore } from "@/store/workflow-store"
import { Bookmark, Brain, Bug, ChevronDown, ChevronUp, Copy, RefreshCw, Share2 } from "lucide-react"
import * as React from "react"
import { useState } from "react"

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

interface CollaborationState {
  mode: "thinking" | "streaming_final" | "complete"
  stages: CollaborationStage[]
  currentStageId?: string
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
              <h2 className="text-2xl font-semibold bg-gradient-to-r from-green-400 to-zinc-400 bg-clip-text text-transparent">
                Your Multi-Agent Workspace Starts Here.
              </h2>
              <p className="bg-gradient-to-r from-green-400 to-zinc-400 bg-clip-text text-transparent max-w-lg">
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
                    <div className="max-w-[80%] text-zinc-100 leading-relaxed text-right">
                      <div className="text-xs text-zinc-400 mb-1">You</div>
                      {message.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-start">
                    <div className="max-w-[90%]">
                      {/* Chain of Thought Toggle */}
                      {message.chainOfThought && (
                        <div
                          className="flex items-center gap-2 text-xs text-zinc-400 ml-1 cursor-pointer hover:text-zinc-300 transition-colors w-fit"
                          onClick={() => toggleThought(message.id)}
                        >
                          <Brain className="w-3.5 h-3.5" />
                          <span>Chain of Thought</span>
                          {expandedThoughts.has(message.id) ? (
                            <ChevronUp className="w-3 h-3" />
                          ) : (
                            <ChevronDown className="w-3 h-3" />
                          )}
                        </div>
                      )}

                      {/* Expanded Chain of Thought */}
                      {message.chainOfThought && expandedThoughts.has(message.id) && (
                        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 ml-1 text-sm text-zinc-300 leading-relaxed">
                          {message.chainOfThought}
                        </div>
                      )}

                      {/* Message Content */}
                      {message.collaboration ? (
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
                        <div className="text-zinc-100 leading-relaxed px-1 py-2">
                          <EnhancedMessageContent
                            content={message.content}
                            role={message.role}
                            images={message.images}
                            onCodePanelOpen={handleCodePanelOpen}
                          />
                        </div>
                      )}

                      {/* Message Metadata - Plain Text */}
                      {message.role === 'assistant' && (
                        <div className="pt-2 text-xs text-zinc-400 flex items-center gap-3 flex-wrap">
                          {/* Model */}
                          {message.modelName && message.modelName !== 'DAC' && (
                            <span>Model: <span className="text-zinc-200 font-medium">{message.modelName}</span></span>
                          )}

                          {/* Accuracy */}
                          {message.confidence && (
                            <span>Accuracy: <span className="text-zinc-200 font-medium">{message.confidence}%</span></span>
                          )}

                          {/* Speed */}
                          {message.processingTime && (
                            <span>Speed: <span className="text-zinc-200 font-medium">{(message.processingTime / 1000).toFixed(2)}s</span></span>
                          )}
                        </div>
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
                    modelName={selectedModel || "Processing"}
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
        <div className="max-w-4xl mx-auto">
          <ImageInputArea
            onSendMessage={onSendMessage}
            selectedModel={selectedModel}
            onModelSelect={onModelSelect}
            isLoading={isLoading}
            autoRoutedModel={autoRoutedModel}
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
