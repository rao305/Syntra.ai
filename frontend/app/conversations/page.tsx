'use client'

import { EnhancedConversationLayout } from '@/components/enhanced-conversation-layout'
import { useRouter } from 'next/navigation'
import * as React from 'react'
// Removed unused auth and conversation hooks
import { runStep, startWorkflow } from '@/app/actions/workflow'
import { SYNTRA_MODELS } from '@/components/syntra-model-selector'
import { apiFetch } from '@/lib/api'
import { useWorkflowStore } from '@/store/workflow-store'
import { toast } from 'sonner'
import { CollabPanel, type CollabPanelState, type CollabStageId } from '@/components/collaborate/CollabPanel'

interface ImageFile {
  file?: File
  url: string
  id: string
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
}

interface ChatHistoryItem {
  id: string
  firstLine: string
  timestamp: string
}

interface ConversationsLandingProps {
  searchParams?: {
    initialMessage?: string | string[]
    [key: string]: string | string[] | undefined
  }
}

export default function ConversationsLanding({ searchParams }: ConversationsLandingProps) {
  const router = useRouter()
  // Simplified without authentication
  const user = null
  const orgId = 'org_demo'
  const accessToken = null
  const loading = false
  const userConversations: any[] = []

  const [messages, setMessages] = React.useState<Message[]>([])
  const [history, setHistory] = React.useState<ChatHistoryItem[]>([])
  const [selectedModel, setSelectedModel] = React.useState('auto')
  const [autoRoutedModel, setAutoRoutedModel] = React.useState<string | null>(null)
  const [isLoading, setIsLoading] = React.useState(false)
  const [currentThreadId, setCurrentThreadId] = React.useState<string | null>(null)

  // Collaboration panel state - 6 stages with dynamic model selection
  const [collabPanel, setCollabPanel] = React.useState<CollabPanelState>({
    active: false,
    stages: [
      { id: "analyst", label: "Analyst", model: "?", status: "pending" },
      { id: "researcher", label: "Researcher", model: "?", status: "pending" },
      { id: "creator", label: "Creator", model: "?", status: "pending" },
      { id: "critic", label: "Critic", model: "?", status: "pending" },
      { id: "council", label: "LLM Council", model: "?", status: "pending" },
      { id: "synth", label: "Synthesizer", model: "?", status: "pending" },
    ]
  })

  // Unwrap the searchParams Promise using React.use()
  const resolvedSearchParams = React.use(searchParams as Promise<typeof searchParams> || Promise.resolve(searchParams))

  const initialMessageFromSearch = React.useMemo(() => {
    if (!resolvedSearchParams?.initialMessage) return null
    const raw = Array.isArray(resolvedSearchParams.initialMessage)
      ? resolvedSearchParams.initialMessage[0]
      : resolvedSearchParams.initialMessage
    if (typeof raw !== 'string') return null
    const trimmed = raw.trim()
    return trimmed.length ? trimmed : null
  }, [resolvedSearchParams?.initialMessage])
  const hasPrefilledInitialMessage = React.useRef(false)

  const { isCollaborateMode, steps, setSteps, updateStep, toggleCollaborateMode } = useWorkflowStore()

  // Helper to update collab panel when a step completes
  const updateCollabPanelForStep = React.useCallback((
    stepRole: string,
    status: "running" | "done" | "error",
    preview?: string,
    duration_ms?: number,
    modelId?: string
  ) => {
    const stageIdMap: Record<string, CollabStageId> = {
      "analyst": "analyst",
      "researcher": "researcher",
      "creator": "creator",
      "critic": "critic",
      "council": "council",
      "synth": "synth",
      // legacy mappings
      "synthesizer": "synth",
      "internal_synth": "synth",
    }

    const stageId = stageIdMap[stepRole] as CollabStageId | undefined
    if (!stageId) return

    setCollabPanel(prev => ({
      ...prev,
      stages: prev.stages.map(s =>
        s.id === stageId
          ? {
              ...s,
              status,
              preview,
              duration_ms,
              model: modelId ?? s.model,
            }
          : s
      )
    }))
  }, [])

  // Execute workflow logic
  const executeWorkflow = React.useCallback(async (currentSteps: typeof steps, userContent: string) => {
    // Get fresh steps from store to ensure we have the latest state
    let localSteps = [...currentSteps]
    setIsLoading(true)

    // Activate collab panel if in collaborate mode
    if (isCollaborateMode) {
      setCollabPanel(prev => ({
        ...prev,
        active: true,
        stages: prev.stages.map(s => ({ ...s, status: "pending" }))
      }))
    }

    console.log(`🚀 Starting workflow execution with ${localSteps.length} steps`)
    console.log(`📋 Initial step states:`, localSteps.map(s => ({
      id: s.id,
      role: s.role,
      status: s.status,
      mode: s.mode
    })))

    // Process steps sequentially - only one at a time
    for (let i = 0; i < localSteps.length; i++) {
      // Refresh steps from store to get latest state (in case of concurrent updates)
      const { steps: storeSteps } = useWorkflowStore.getState()
      const storeStep = storeSteps.find(s => s.id === localSteps[i].id)
      if (storeStep) {
        localSteps[i] = { ...storeStep }
      }

      const step = localSteps[i]

      console.log(`🔍 Processing step ${i + 1}/${localSteps.length}: ${step.id} (${step.role}) - current status: ${step.status}`)

      // Skip steps that are already completed (done, error, cancelled)
      // Process steps that are pending, running, or awaiting_user (if continuing after approval)
      if (step.status === "done" || step.status === "error" || step.status === "cancelled") {
        console.log(`⏭️ Skipping step ${step.id} - status: ${step.status} (already completed)`)
        continue
      }

      // Double-check: if step has an error, log it and skip
      if (step.error) {
        console.warn(`⚠️ Step ${step.id} has an error from previous run:`, step.error)
        console.log(`⏭️ Skipping step ${step.id} due to previous error`)
        continue
      }

      // If step is awaiting_user, it means it's waiting for approval - skip it for now
      // (It should have been set to "done" before continue is called)
      if (step.status === "awaiting_user") {
        console.log(`⏸️ Step ${step.id} is awaiting approval - skipping`)
        setIsLoading(false)
        return
      }

      // Ensure we're processing steps in order - don't skip ahead
      // Check if any previous step is still pending or awaiting_user
      const previousIncomplete = localSteps.slice(0, i).some(s =>
        s.status === "pending" || s.status === "awaiting_user" || s.status === "running"
      )
      if (previousIncomplete) {
        const incompleteSteps = localSteps.slice(0, i).filter(s =>
          s.status === "pending" || s.status === "awaiting_user" || s.status === "running"
        )
        console.log(`⏸️ Waiting for previous steps to complete before processing ${step.id}`)
        console.log(`📋 Incomplete previous steps:`, incompleteSteps.map(s => ({
          id: s.id,
          role: s.role,
          status: s.status
        })))
        setIsLoading(false)
        return
      }

      // Log step order to ensure we're processing in correct sequence
      console.log(`📝 Step processing order check:`, {
        currentIndex: i,
        currentStep: { id: step.id, role: step.role, status: step.status },
        previousSteps: localSteps.slice(0, i).map(s => ({ id: s.id, role: s.role, status: s.status }))
      })

      // Update UI to show running
      console.log(`🔄 Starting step ${step.id} (${step.role}) - mode: ${step.mode}`)
      updateStep(step.id, { status: "running" })

      // Update collab panel if in collaborate mode
      // Note: step.model represents the selected model ID from the router
      if (isCollaborateMode) {
        updateCollabPanelForStep(step.role, "running", undefined, undefined, step.model)
      }

      try {
        // Run the step on server - this will wait for completion
        // Add a client-side timeout as a safety net (server has 120s, we'll give it 130s)
        console.log(`⏳ Calling runStep for ${step.id} (${step.role}) with ${step.model}...`)
        const stepTimeout = new Promise((_, reject) => {
          setTimeout(() => reject(new Error(`Step ${step.id} execution exceeded 130 seconds`)), 130000)
        })

        const result = await Promise.race([
          runStep(step.id, userContent, localSteps),
          stepTimeout
        ]) as Awaited<ReturnType<typeof runStep>>

        console.log(`✅ runStep completed for ${step.id}, status: ${result?.status}`)
        console.log(`📦 Raw result from server:`, JSON.stringify(result, null, 2))

        if (!result) {
          console.error(`❌ No result returned from step ${step.id}`)
          updateStep(step.id, {
            status: "error",
            error: { message: "No response from server", provider: step.model, type: "network" }
          })
          setIsLoading(false)
          return
        }

        // Log all properties of the result for debugging
        console.log(`📊 Result properties:`, {
          keys: Object.keys(result),
          status: result.status,
          hasOutputDraft: 'outputDraft' in result,
          hasErrorMessage: 'errorMessage' in result,
          errorMessage: (result as any).errorMessage,
          errorProvider: (result as any).errorProvider,
          errorType: (result as any).errorType
        })

        console.log(`✅ Step ${step.id} (${step.role}) completed with status: ${result.status}`)

        // Extract error from result - handle both nested and flat error structures
        const resultAny = result as any
        let error: { message: string; provider?: string; type?: "config" | "network" | "rate_limit" | "timeout" | "unknown" } | undefined = undefined

        if (result.status === "error") {
          // Map error type string to valid type
          const mapErrorType = (type: string | undefined): "config" | "network" | "rate_limit" | "timeout" | "unknown" => {
            const validTypes = ["config", "network", "rate_limit", "timeout", "unknown"]
            return validTypes.includes(type || "") ? type as any : "unknown"
          }

          // Check for flat error properties (new format)
          if (resultAny.errorMessage) {
            error = {
              message: resultAny.errorMessage,
              provider: resultAny.errorProvider || step.model,
              type: mapErrorType(resultAny.errorType)
            }
          }
          // Check for nested error object (old format)
          else if (resultAny.error && typeof resultAny.error === 'object') {
            error = {
              message: resultAny.error.message || "Unknown error",
              provider: resultAny.error.provider || step.model,
              type: mapErrorType(resultAny.error.type)
            }
          }
          // Fallback error
          else {
            error = {
              message: `${step.role} step failed with ${step.model}. Check API keys and model availability.`,
              provider: step.model,
              type: "unknown"
            }
          }
        }

        console.log(`📊 Step result details:`, {
          hasOutput: !!result.outputDraft,
          outputLength: result.outputDraft?.length || 0,
          status: result.status,
          hasError: !!error,
          errorDetails: error,
          fullResult: JSON.stringify(result, null, 2)
        })

        const { outputDraft, status, metadata } = result

        // Update UI with result
        updateStep(step.id, {
          outputDraft,
          outputFinal: status === "done" ? outputDraft : undefined,
          status: status as any,
          metadata,
          error
        })

        // Update collab panel if in collaborate mode and step is done
        if (isCollaborateMode && status === "done" && outputDraft) {
          // Extract preview (first 150 characters)
          const preview = outputDraft.substring(0, 150).replace(/\n/g, ' ')
          const duration = metadata?.processing_time_ms || metadata?.latency_ms || undefined
          updateCollabPanelForStep(step.role, "done", preview, duration, step.model)
        }

        // Update local steps array for next iteration context
        localSteps = localSteps.map(s => s.id === step.id ? {
          ...s,
          outputDraft,
          outputFinal: status === "done" ? outputDraft : undefined,
          status: status as any,
          metadata,
          error
        } : s)

        // IMPORTANT: Refresh ALL steps from store to ensure we have latest state
        // This prevents issues where the next iteration might see stale data
        const { steps: allStoreSteps } = useWorkflowStore.getState()
        localSteps = localSteps.map(localStep => {
          const storeStep = allStoreSteps.find(s => s.id === localStep.id)
          return storeStep || localStep
        })

        // Log current step states for debugging
        console.log(`📋 Current step states after update:`, localSteps.map(s => ({
          id: s.id,
          role: s.role,
          status: s.status,
          mode: s.mode
        })))

        // Add step output as a message in the chat for visibility
        // BUT: Skip this when in Collaborate mode - we only show the final answer
        const { isCollaborateMode } = useWorkflowStore.getState()
        if (outputDraft && status !== "error" && !isCollaborateMode) {
          const modelName = step.model === "gpt" ? "GPT" :
            step.model === "gemini" ? "Gemini" :
              step.model === "perplexity" ? "Perplexity" :
                step.model === "kimi" ? "Kimi" : step.model

          const stepMessage: Message = {
            id: `step-${step.id}-${Date.now()}`,
            role: 'assistant',
            content: `## ${step.role.charAt(0).toUpperCase() + step.role.slice(1)} (${modelName})\n\n${outputDraft}`,
            timestamp: new Date().toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
            }),
            modelId: step.model,
            modelName: modelName,
            reasoningType: step.role === "analyst" ? "analysis" :
              step.role === "researcher" ? "research" :
                step.role === "creator" ? "creative" :
                  step.role === "critic" ? "analysis" : "conversation"
          }
          setMessages((prev) => [...prev, stepMessage])
        }

        // If error, stop workflow
        if (status === "error") {
          // Error is already extracted above with proper message
          let errorMsg = error?.message || `${step.role} step failed with ${step.model}. Check API keys and model availability.`
          const errorType = error?.type || "unknown"

          // Try to parse nested JSON error messages (from API responses)
          try {
            if (errorMsg.startsWith('{') && errorMsg.includes('error')) {
              const parsed = JSON.parse(errorMsg)
              if (parsed.error?.message) {
                errorMsg = `${parsed.error.message} (${parsed.error.type || 'API error'})`
              }
            }
          } catch {
            // Keep original message if parsing fails
          }

          console.error(`❌ Workflow stopped due to error in step ${step.id} (${step.role}):`)
          console.error(`   Error message: ${errorMsg}`)
          console.error(`   Error type: ${errorType}`)
          console.error(`   Error provider: ${error?.provider || step.model}`)

          // Update step with proper error (already done above, but ensure it's set)
          updateStep(step.id, {
            status: "error",
            error: {
              message: errorMsg,
              provider: error?.provider || step.model,
              type: errorType as any
            }
          })

          // Create a user-friendly error message
          const modelName = step.model === "gpt" ? "GPT (OpenAI)" :
            step.model === "gemini" ? "Gemini (Google)" :
              step.model === "perplexity" ? "Perplexity" :
                step.model === "kimi" ? "Kimi (Moonshot)" : step.model

          const errorMessage: Message = {
            id: `error-${step.id}-${Date.now()}`,
            role: 'assistant',
            content: `**Error in ${step.role} step using ${modelName}**\n\n${errorMsg}\n\n**How to fix:**\n- Check that the API key for ${modelName} is set correctly in your backend \`.env\` file\n- Verify the API key is valid and not expired\n- Check your API usage limits`,
            timestamp: new Date().toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
            }),
          }
          setMessages((prev) => [...prev, errorMessage])
          setIsLoading(false)
          return
        }

        // If manual mode, stop here and wait for user approval
        if (status === "awaiting_user") {
          console.log(`⏸️ Workflow paused at step ${step.id} (${step.role}) - waiting for user approval`)
          setIsLoading(false)
          return
        }

        // If step completed successfully, continue to next step
        console.log(`✅ Step ${step.id} (${step.role}) completed successfully with status: ${status}`)

        // Log next step that will be processed
        const nextStepIndex = i + 1
        if (nextStepIndex < localSteps.length) {
          const nextStep = localSteps[nextStepIndex]
          console.log(`➡️ Next step to process: ${nextStep.id} (${nextStep.role}) - current status: ${nextStep.status}, mode: ${nextStep.mode}`)

          // If next step is pending and in auto mode, it should run automatically
          if (nextStep.status === "pending" && nextStep.mode === "auto") {
            console.log(`🚀 Next step ${nextStep.id} is pending and in auto mode - will execute automatically`)
          } else if (nextStep.status === "pending" && nextStep.mode === "manual") {
            console.log(`⏸️ Next step ${nextStep.id} is pending and in manual mode - will wait for approval`)
          }
        } else {
          console.log(`🏁 No more steps to process (reached end of workflow)`)
        }

        // Small delay to allow UI to update between steps
        await new Promise(resolve => setTimeout(resolve, 100))

        // Continue to next iteration of the loop
        console.log(`🔄 Continuing workflow loop to next step...`)
      } catch (error: any) {
        console.error(`❌ Step ${step.id} (${step.role}) failed with error:`, error)
        console.error('Error details:', {
          message: error?.message,
          stack: error?.stack,
          name: error?.name,
          errorType: typeof error,
          errorString: String(error)
        })

        // Check if it's a timeout error
        const isTimeout = error?.message?.includes("exceeded") || error?.message?.includes("timeout") || error?.message?.includes("timed out")
        const errorType = isTimeout ? "timeout" : "unknown"

        updateStep(step.id, {
          status: "error",
          error: {
            message: error?.message || `Step ${step.role} failed with ${step.model}`,
            provider: step.model,
            type: errorType
          }
        })

        // Add error message to chat
        const errorMessage: Message = {
          id: `error-${step.id}-${Date.now()}`,
          role: 'assistant',
          content: `**Error in ${step.role} step (${step.model}):** ${error?.message || "Step execution failed"}\n\nPlease check your API keys and model availability.`,
          timestamp: new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
          }),
        }
        setMessages((prev) => [...prev, errorMessage])

        setIsLoading(false)
        return
      }
    }

    // Check if all steps are completed, especially the synthesizer
    const allStepsCompleted = localSteps.every(s => s.status === "done" || s.status === "error")
    const synthesizerStep = localSteps.find(s => s.role === "synthesizer")

    // If synthesizer completed, create clean final message and exit collaboration mode
    if (allStepsCompleted && synthesizerStep && synthesizerStep.status === "done" && synthesizerStep.outputFinal) {
      // Get clean output from synthesizer (this is the final answer)
      let finalContent = synthesizerStep.outputFinal

      // Clean up markdown artifacts while preserving valid markdown for rendering
      finalContent = finalContent
        // Remove standalone separator lines (--- on their own line)
        .replace(/^\s*-{3,}\s*$/gm, '')
        // Remove quadruple asterisks (invalid markdown)
        .replace(/\*\*\*\*/g, '')
        // Remove triple asterisks (invalid markdown, but keep ** for bold)
        .replace(/\*\*\*(?!\*)/g, '')
        // Remove headers deeper than h3 (keep h1, h2, h3)
        .replace(/^#{4,}\s+/gm, '### ')
        // Clean up excessive whitespace
        .replace(/\n{3,}/g, '\n\n')
        // Remove leading/trailing separators
        .replace(/^[\s\-*]+\n/gm, '')
        .replace(/\n[\s\-*]+$/gm, '')
        .trim()

      // Create clean final message - content will be rendered as markdown by EnhancedMessageContent
      // LaTeX and code blocks will be properly rendered
      const finalMessage: Message = {
        id: `final-${Date.now()}`,
        role: 'assistant',
        content: finalContent, // Clean markdown content, will be rendered properly
        timestamp: new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        }),
        modelId: 'collaboration',
        modelName: 'Multi-Agent Collaboration',
        reasoningType: 'analysis'
      }

      setMessages((prev) => [...prev, finalMessage])

      // Deactivate collab panel
      setCollabPanel(prev => ({
        ...prev,
        active: false
      }))

      // Exit collaboration mode and close modal
      console.log('✅ Workflow complete - exiting collaboration mode')
      setTimeout(() => {
        toggleCollaborateMode() // This will close the collaboration UI
        setIsLoading(false) // Ensure loading state is cleared
      }, 300) // Small delay to show completion
    }

    console.log(`🏁 All workflow steps completed`)
    setIsLoading(false)
  }, [updateStep, setMessages, toggleCollaborateMode, isCollaborateMode, updateCollabPanelForStep])

  const handleContinueWorkflow = React.useCallback(() => {
    // Find the last user message to use as context
    const lastUserMessage = messages.slice().reverse().find(m => m.role === 'user')?.content || ""
    // Get the latest steps from the store to ensure we have the updated statuses
    const { steps: latestSteps } = useWorkflowStore.getState()
    console.log('🔄 Continuing workflow with steps:', latestSteps.map(s => ({ id: s.id, role: s.role, status: s.status })))

    // Check if there are any steps that need processing
    const hasPendingSteps = latestSteps.some(s =>
      s.status === "pending" || s.status === "running" || s.status === "awaiting_user"
    )

    if (!hasPendingSteps) {
      console.log('✅ All steps completed, workflow finished')
      setIsLoading(false)
      return
    }

    executeWorkflow(latestSteps, lastUserMessage)
  }, [messages, executeWorkflow])

  // Build chat history
  React.useEffect(() => {
    if (userConversations.length > 0) {
      const historyItems: ChatHistoryItem[] = userConversations
        .slice(0, 20)
        .map((conv) => ({
          id: conv.id,
          firstLine: conv.title || conv.lastMessagePreview || 'Untitled conversation',
          timestamp: new Date(conv.updatedAt).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
          }),
        }))
      setHistory(historyItems)
    }
  }, [userConversations])

  const handleNewChat = () => {
    // Reset conversation state for new chat
    setMessages([])
    setCurrentThreadId(null)
    console.log('🆕 Started new chat - reset thread ID and messages')
  }

  const handleHistoryClick = (id: string) => {
    router.push(`/conversations/${id}`)
  }

  const handleModelSelect = (modelId: string) => {
    setSelectedModel(modelId)
    const modelName = SYNTRA_MODELS.find((m) => m.id === modelId)?.name
    toast.success(`Switched to ${modelName}`)
  }

  const handleSendMessage = async (content: string, images?: ImageFile[]) => {
    console.log('🚀 handleSendMessage called with content:', content, 'images:', images)

    if (!content.trim() && (!images || images.length === 0)) {
      console.log('❌ Content and images are empty, returning early')
      return
    }

    if (isCollaborateMode) {
      console.log('🧠 Starting collaborative workflow')

      // Add user message
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: content.trim(),
        images: images,
        timestamp: new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        }),
      }
      setMessages((prev) => [...prev, userMessage])

      try {
        console.log('🔧 Initializing workflow steps...')
        const initialSteps = await startWorkflow(content.trim())
        console.log('✅ Workflow steps initialized:', initialSteps.length, 'steps')

        // Get the current mode from the store (set by the Auto/Manual toggle)
        const { mode: currentMode } = useWorkflowStore.getState()
        console.log(`🔄 Using workflow mode from store: ${currentMode}`)

        // Set all steps to the current mode from the store
        const stepsWithMode = initialSteps.map(step => ({
          ...step,
          mode: currentMode
        }))
        console.log(`✅ Set all steps to ${currentMode} mode`)
        setSteps(stepsWithMode)

        // Start execution
        console.log('🚀 Starting workflow execution')
        await executeWorkflow(stepsWithMode, content.trim())
        console.log('🏁 Workflow execution completed')

      } catch (error: any) {
        console.error("❌ Workflow error:", error)
        console.error('Error details:', {
          message: error.message,
          stack: error.stack,
          name: error.name
        })

        // Add error message to chat
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Sorry, there was an error with the collaborative workflow: ${error.message || 'Unknown error'}`,
          timestamp: new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
          }),
        }
        setMessages((prev) => [...prev, errorMessage])
        setIsLoading(false)
      }
      return
    }

    console.log('🔐 Using demo mode - orgId:', orgId)

    console.log('✅ Auth passed, creating user message')

    // Add user message immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      images: images,
      timestamp: new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      }),
    }

    console.log('💬 Adding user message to state:', userMessage)
    setMessages((prev) => {
      const newMessages = [...prev, userMessage]
      console.log('📝 New messages state:', newMessages)
      return newMessages
    })
    setIsLoading(true)
    console.log('⏳ Set loading to true')

    try {
      console.log('🔍 Finding model data for:', selectedModel)
      const selectedModelData = SYNTRA_MODELS.find((m) => m.id === selectedModel)
      console.log('🤖 Selected model data:', selectedModelData)

      let threadId: string

      if (currentThreadId) {
        // Use existing thread for follow-up messages
        console.log('🔄 Using existing thread:', currentThreadId)
        threadId = currentThreadId
      } else {
        // Create new thread for first message
        console.log('🧵 Creating new thread...')
        const threadResponse = await apiFetch<{
          thread_id: string
          created_at: string
        }>(`/threads/`, {
          method: 'POST',
          body: JSON.stringify({
            title: content.trim().substring(0, 50),
            description: '',
          }),
        })

        console.log('✅ Thread created:', threadResponse)
        threadId = threadResponse.thread_id
        setCurrentThreadId(threadId)
      }

      // Prepare request body
      const requestBody: any = {
        content: content.trim(),
        collaboration_mode: isCollaborateMode,
      }
      
      // Add images if present - convert to attachments format
      if (images && images.length > 0) {
        requestBody.attachments = images.map((img, index) => ({
          type: "image",
          name: img.file?.name || `image-${index + 1}`,
          url: img.url,
          mimeType: img.file?.type || "image/jpeg"
        }))
      }

      // Only add model_preference if not using auto mode
      if (selectedModel !== 'auto' && selectedModelData?.provider) {
        requestBody.model_preference = selectedModelData.provider
      }

      // Step 2: Add message to the thread
      const messageResponse = await apiFetch<{
        user_message: { id: string; content: string }
        assistant_message: {
          id: string;
          content: string;
          provider?: string;
          model?: string;
          meta?: {
            latency_ms?: number;
            request_id?: string;
          };
        }
      }>(`/threads/${threadId}/messages`, {
        method: 'POST',
        body: JSON.stringify(requestBody),
      })

      console.log('📋 Message response:', messageResponse)
      console.log('🤖 Assistant message data:', messageResponse.assistant_message)
      console.log('🔧 Provider:', messageResponse.assistant_message.provider)
      console.log('🔧 Model:', messageResponse.assistant_message.model)

      // Determine reasoning type based on content
      const determineReasoningType = (content: string, query: string): 'coding' | 'analysis' | 'creative' | 'research' | 'conversation' => {
        const lowerContent = content.toLowerCase()
        const lowerQuery = query.toLowerCase()

        if (lowerContent.includes('```') || lowerQuery.includes('code') || lowerQuery.includes('function')) {
          return 'coding'
        }
        if (lowerQuery.includes('analyze') || lowerQuery.includes('explain') || lowerQuery.includes('why')) {
          return 'analysis'
        }
        if (lowerQuery.includes('create') || lowerQuery.includes('write') || lowerQuery.includes('story')) {
          return 'creative'
        }
        if (lowerQuery.includes('what') || lowerQuery.includes('research') || lowerQuery.includes('find')) {
          return 'research'
        }
        return 'conversation'
      }

      // Add assistant message with enhanced properties
      const assistantMessage: Message = {
        id: messageResponse.assistant_message.id,
        role: 'assistant',
        content: messageResponse.assistant_message.content,
        chainOfThought: selectedModelData
          ? `I analyzed your request using ${selectedModelData.name}. This model excels at ${selectedModelData.description?.toLowerCase() || 'advanced language processing'}. I applied systematic reasoning to understand your needs, gathered relevant context, synthesized the information, and formulated a comprehensive response. The reasoning process included: pattern recognition, logical inference, and knowledge integration to provide you with the most accurate and helpful answer.`
          : undefined,
        timestamp: new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        }),
        modelId: selectedModel,
        modelName: (() => {
          const model = messageResponse.assistant_message.model;
          const provider = messageResponse.assistant_message.provider;

          // Check model field first (contains actual model identifier)
          if (model) {
            const lowerModel = model.toLowerCase();
            // OpenAI / ChatGPT models
            if (lowerModel.includes('gpt')) return 'GPT';
            // Google Gemini models
            if (lowerModel.includes('gemini')) return 'Gemini';
            // Perplexity models (includes sonar, llama variants)
            if (lowerModel.includes('perplexity') || lowerModel.includes('sonar') || lowerModel.includes('llama')) {
              return 'Perplexity';
            }
            // Kimi / Moonshot models (Zhipu AI)
            if (lowerModel.includes('kimi') || lowerModel.includes('moonshot')) return 'Kimi';
            // OpenRouter (will have format like "openai/gpt-4", "google/gemini", etc)
            if (lowerModel.includes('openrouter') || lowerModel.includes('/')) {
              // Extract provider name from OpenRouter format
              const parts = lowerModel.split('/');
              if (parts.length > 1) {
                const providerPart = parts[0].toLowerCase();
                if (providerPart.includes('openai') || providerPart.includes('gpt')) return 'GPT';
                if (providerPart.includes('google') || providerPart.includes('gemini')) return 'Gemini';
                if (providerPart.includes('perplexity')) return 'Perplexity';
                if (providerPart.includes('zhipu') || providerPart.includes('kimi')) return 'Kimi';
              }
              return 'OpenRouter';
            }
          }

          // Fallback to provider field if model not available
          if (provider) {
            const lowerProvider = provider.toLowerCase();
            if (lowerProvider === 'gemini' || lowerProvider === 'google') return 'Gemini';
            if (lowerProvider === 'openai') return 'GPT';
            if (lowerProvider === 'perplexity') return 'Perplexity';
            if (lowerProvider === 'kimi' || lowerProvider === 'zhipu') return 'Kimi';
            if (lowerProvider === 'openrouter') return 'OpenRouter';
            // Capitalize first letter for unknown providers
            return provider.charAt(0).toUpperCase() + provider.slice(1);
          }

          return selectedModelData?.name || 'DAC';
        })(),
        reasoningType: determineReasoningType(messageResponse.assistant_message.content, content),
        confidence: Math.floor(85 + Math.random() * 15),
        processingTime: messageResponse.assistant_message.meta?.latency_ms ?
          Math.round(messageResponse.assistant_message.meta.latency_ms) :
          Math.floor(800 + Math.random() * 1200),
      }

      setMessages((prev) => [...prev, assistantMessage])

      // Capture the auto-routed model if using auto mode
      if (selectedModel === 'auto' && assistantMessage.modelName) {
        setAutoRoutedModel(assistantMessage.modelName)
      }

    } catch (error: any) {
      console.error('💥 Error sending message:', error)
      console.error('💥 Error details:', {
        message: error.message,
        stack: error.stack,
        name: error.name
      })
      toast.error('Failed to send message. Please try again.')
      // Remove the user message if the API call failed
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id))
    } finally {
      console.log('🏁 Finally block - setting loading to false')
      setIsLoading(false)
    }
  }

  // No loading state needed since we removed auth

  React.useEffect(() => {
    if (!initialMessageFromSearch || hasPrefilledInitialMessage.current) return

    hasPrefilledInitialMessage.current = true
    void handleSendMessage(initialMessageFromSearch)

    if (typeof window !== 'undefined' && window.location.search.includes('initialMessage')) {
      const url = new URL(window.location.href)
      url.searchParams.delete('initialMessage')
      const nextSearch = url.searchParams.toString()
      const nextUrl = `${url.pathname}${nextSearch ? `?${nextSearch}` : ''}${url.hash}`
      router.replace(nextUrl, { scroll: false })
    }
  }, [handleSendMessage, initialMessageFromSearch, router])

  return (
    <EnhancedConversationLayout
      messages={messages}
      history={history}
      onSendMessage={handleSendMessage}
      onNewChat={handleNewChat}
      onHistoryClick={handleHistoryClick}
      isLoading={isLoading}
      selectedModel={selectedModel}
      onModelSelect={handleModelSelect}
      onContinueWorkflow={handleContinueWorkflow}
      autoRoutedModel={autoRoutedModel}
      collabPanel={collabPanel}
    />
  )
}
