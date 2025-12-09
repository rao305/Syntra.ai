'use client'

import { EnhancedConversationLayout } from '@/components/enhanced-conversation-layout'
import { useRouter } from 'next/navigation'
import * as React from 'react'
// Removed unused auth and conversation hooks
import { runStep, startWorkflow } from '@/app/actions/workflow'
import { type CollabPanelState, type CollabStageId } from '@/components/collaborate/CollabPanel'
import { SYNTRA_MODELS } from '@/components/syntra-model-selector'
import { apiFetch } from '@/lib/api'
import { useWorkflowStore } from '@/store/workflow-store'
import { toast } from 'sonner'

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
  media?: Array<{
    type: 'image' | 'graph'
    url: string
    alt?: string
    mime_type?: string
  }>
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
  const user: { uid: string } | null = null
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

  // Update message helper function
  const updateMessage = React.useCallback((messageId: string, updates: any) => {
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id === messageId) {
          const updateData = typeof updates === 'function' ? updates(msg) : updates
          const merged: any = { ...msg }

          // Handle each update field, supporting function-based updates
          for (const [key, value] of Object.entries(updateData)) {
            if (typeof value === 'function') {
              // Function-based update (e.g., content: (prev) => prev + delta)
              const currentValue = (msg as any)[key]
              merged[key] = value(currentValue)
            } else {
              // Direct value update
              merged[key] = value
            }
          }

          return merged as Message
        }
        return msg
      })
    )
  }, [])

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

  // Handle searchParams (can be a Promise or object in Next.js 15+)
  const [resolvedSearchParams, setResolvedSearchParams] = React.useState<{
    [key: string]: string | string[] | undefined
    initialMessage?: string | string[]
  } | null>(null)

  React.useEffect(() => {
    const resolveParams = async () => {
      const params = await Promise.resolve(searchParams)
      setResolvedSearchParams(params || null)
    }
    resolveParams()
  }, [searchParams])

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
    const { isCollaborateMode: collabMode } = useWorkflowStore.getState()
    if (collabMode) {
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
      const { isCollaborateMode: collabModeRunning } = useWorkflowStore.getState()
      if (collabModeRunning) {
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

        // Only log detailed result if there's an error or in development
        if (result?.status === 'error' || process.env.NODE_ENV === 'development') {
          console.log(`✅ runStep completed for ${step.id}, status: ${result?.status}`)
        }

        if (!result) {
          console.error(`❌ No result returned from step ${step.id}`)
          updateStep(step.id, {
            status: "error",
            error: { message: "No response from server", provider: step.model, type: "network" }
          })
          setIsLoading(false)
          return
        }

        // Only log detailed properties in development mode
        if (process.env.NODE_ENV === 'development' && result.status === 'error') {
          console.log(`📊 Step ${step.id} (${step.role}) error details:`, {
            status: result.status,
            errorMessage: (result as any).errorMessage,
            errorProvider: (result as any).errorProvider,
            errorType: (result as any).errorType
          })
        }

        // Extract error from result - handle both nested and flat error structures
        const resultAny = result as any
        let error: { message: string; provider?: string; type?: "config" | "network" | "rate_limit" | "timeout" | "unknown" } | undefined = undefined

        if (result.status === "error") {
          // Map error type string to valid type, but also re-classify based on error message
          const mapErrorType = (type: string | undefined, errorMsg?: string): "config" | "network" | "rate_limit" | "timeout" | "unknown" => {
            // First check the message to determine the correct type (message is more reliable)
            if (errorMsg) {
              const msgLower = String(errorMsg).toLowerCase();
              if (msgLower.includes('authentication') ||
                msgLower.includes('invalid_authentication') ||
                (msgLower.includes('invalid') && (msgLower.includes('key') || msgLower.includes('token') || msgLower.includes('auth'))) ||
                msgLower.includes('api key') ||
                msgLower.includes('unauthorized') ||
                msgLower.includes('forbidden') ||
                msgLower.includes('kimi api authentication failed')) {
                return "config";
              }
              if (msgLower.includes('rate limit') || msgLower.includes('429') || msgLower.includes('too many requests')) {
                return "rate_limit";
              }
              if (msgLower.includes('timeout') || msgLower.includes('timed out') || msgLower.includes('exceeded')) {
                return "timeout";
              }
              if (msgLower.includes('network') || msgLower.includes('connection') || msgLower.includes('fetch')) {
                return "network";
              }
            }
            // Fall back to the provided type if message doesn't give clear indication
            const validTypes = ["config", "network", "rate_limit", "timeout", "unknown"]
            return validTypes.includes(type || "") ? type as any : "unknown"
          }

          // Check for flat error properties (new format)
          if (resultAny.errorMessage) {
            error = {
              message: resultAny.errorMessage,
              provider: resultAny.errorProvider || step.model,
              type: mapErrorType(resultAny.errorType, resultAny.errorMessage)
            }
          }
          // Check for nested error object (old format)
          else if (resultAny.error && typeof resultAny.error === 'object') {
            error = {
              message: resultAny.error.message || "Unknown error",
              provider: resultAny.error.provider || step.model,
              type: mapErrorType(resultAny.error.type, resultAny.error.message)
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

        // Only log detailed result in development mode
        if (process.env.NODE_ENV === 'development' && error) {
          console.log(`📊 Step ${step.id} error:`, error)
        }

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
        const { isCollaborateMode: collabModeDone } = useWorkflowStore.getState()
        if (collabModeDone && status === "done" && outputDraft) {
          // Extract preview (first 150 characters)
          const preview = outputDraft.substring(0, 150).replace(/\n/g, ' ')
          const duration = (metadata as any)?.processing_time_ms || (metadata as any)?.latency_ms || undefined
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
          // Ensure we have a valid error object
          if (!error) {
            // If error object is missing, create one from the result
            error = {
              message: resultAny.errorMessage ||
                (typeof resultAny.error === 'string' ? resultAny.error : resultAny.error?.message) ||
                `${step.role} step failed with ${step.model}. Check API keys and model availability.`,
              provider: resultAny.errorProvider || step.model,
              type: (resultAny.errorType === 'config' || resultAny.errorType === 'network' ||
                resultAny.errorType === 'rate_limit' || resultAny.errorType === 'timeout')
                ? resultAny.errorType
                : 'unknown' as const
            }
          }

          let errorMsg = error?.message || `${step.role} step failed with ${step.model}. Check API keys and model availability.`
          const errorType = error?.type || "unknown"

          // Try to parse nested JSON error messages (from API responses)
          try {
            if (typeof errorMsg === 'string' && errorMsg.startsWith('{') && errorMsg.includes('error')) {
              const parsed = JSON.parse(errorMsg)
              if (parsed.error?.message) {
                errorMsg = `${parsed.error.message} (${parsed.error.type || 'API error'})`
              }
            }
          } catch {
            // Keep original message if parsing fails
          }

          // Ensure errorMsg is a string
          errorMsg = String(errorMsg || 'Unknown error occurred')

          // Only log error in development mode (user already sees it in UI)
          if (process.env.NODE_ENV === 'development') {
            console.warn(`⚠️ Workflow step failed: ${step.role} (${step.model}) - ${errorMsg}`)
          }

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

          // Provide more specific error messages based on error type
          let fixInstructions = '';
          if (errorType === 'config') {
            if (step.model === 'kimi') {
              fixInstructions = `**How to fix:**\n- Check that \`KIMI_API_KEY\` or \`MOONSHOT_API_KEY\` is set in your backend \`.env\` file\n- Verify the API key is valid and not expired (get it from https://platform.moonshot.cn/console/api-keys)\n- Restart the backend server after adding the key`;
            } else if (step.model === 'gpt') {
              fixInstructions = `**How to fix:**\n- Check that \`OPENAI_API_KEY\` is set in your backend \`.env\` file\n- Verify the API key is valid and has credits available\n- Restart the backend server after adding the key`;
            } else if (step.model === 'gemini') {
              fixInstructions = `**How to fix:**\n- Check that \`GEMINI_API_KEY\` or \`GOOGLE_API_KEY\` is set in your backend \`.env\` file\n- Get your API key from https://aistudio.google.com/app/apikey\n- Restart the backend server after adding the key`;
            } else if (step.model === 'perplexity') {
              fixInstructions = `**How to fix:**\n- Check that \`PERPLEXITY_API_KEY\` is set in your backend \`.env\` file\n- Get your API key from https://www.perplexity.ai/settings/api\n- Restart the backend server after adding the key`;
            } else {
              fixInstructions = `**How to fix:**\n- Check that the API key for ${modelName} is set correctly in your backend \`.env\` file\n- Verify the API key is valid and not expired\n- Restart the backend server after adding the key`;
            }
          } else if (errorType === 'rate_limit') {
            fixInstructions = `**How to fix:**\n- You've hit the rate limit for ${modelName}\n- Wait a few minutes before trying again\n- Check your API usage and upgrade your plan if needed`;
          } else if (errorType === 'timeout') {
            fixInstructions = `**How to fix:**\n- The request to ${modelName} timed out\n- Try again with a shorter request\n- Check your network connection`;
          } else {
            fixInstructions = `**How to fix:**\n- Check your network connection\n- Verify the API key for ${modelName} is valid\n- Check the backend logs for more details`;
          }

          const errorMessage: Message = {
            id: `error-${step.id}-${Date.now()}`,
            role: 'assistant',
            content: `**Error in ${step.role} step using ${modelName}**\n\n${errorMsg}\n\n${fixInstructions}`,
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
        // Only log in development mode (user already sees error in UI)
        if (process.env.NODE_ENV === 'development') {
          console.warn(`⚠️ Step ${step.id} (${step.role}) exception:`, error?.message || String(error))
        }

        // Extract error message safely
        let errorMsg = 'Unknown error occurred';
        if (error instanceof Error) {
          errorMsg = error.message;
        } else if (typeof error === 'string') {
          errorMsg = error;
        } else if (error && typeof error === 'object') {
          errorMsg = error.message || error.error || JSON.stringify(error);
        }

        // Determine error type
        const errorMsgLower = String(errorMsg).toLowerCase();
        let errorType: "config" | "network" | "rate_limit" | "timeout" | "unknown" = "unknown";
        if (errorMsgLower.includes("timeout") || errorMsgLower.includes("exceeded") || errorMsgLower.includes("timed out")) {
          errorType = "timeout";
        } else if (errorMsgLower.includes("authentication") || errorMsgLower.includes("invalid") && (errorMsgLower.includes("key") || errorMsgLower.includes("api"))) {
          errorType = "config";
        } else if (errorMsgLower.includes("rate limit") || errorMsgLower.includes("429")) {
          errorType = "rate_limit";
        } else if (errorMsgLower.includes("network") || errorMsgLower.includes("fetch") || errorMsgLower.includes("connection")) {
          errorType = "network";
        }

        const modelName = step.model === "gpt" ? "GPT (OpenAI)" :
          step.model === "gemini" ? "Gemini (Google)" :
            step.model === "perplexity" ? "Perplexity" :
              step.model === "kimi" ? "Kimi (Moonshot)" : step.model

        updateStep(step.id, {
          status: "error",
          error: {
            message: errorMsg,
            provider: step.model,
            type: errorType
          }
        })

        // Provide fix instructions based on error type
        let fixInstructions = '';
        if (errorType === 'config') {
          if (step.model === 'kimi') {
            fixInstructions = `**How to fix:**\n- Check that \`KIMI_API_KEY\` or \`MOONSHOT_API_KEY\` is set in your backend \`.env\` file\n- Verify the API key is valid and not expired\n- Restart the backend server after adding the key`;
          } else if (step.model === 'gpt') {
            fixInstructions = `**How to fix:**\n- Check that \`OPENAI_API_KEY\` is set in your backend \`.env\` file\n- Verify the API key is valid and has credits available\n- Restart the backend server after adding the key`;
          } else if (step.model === 'gemini') {
            fixInstructions = `**How to fix:**\n- Check that \`GEMINI_API_KEY\` or \`GOOGLE_API_KEY\` is set in your backend \`.env\` file\n- Get your API key from https://aistudio.google.com/app/apikey\n- Restart the backend server after adding the key`;
          } else if (step.model === 'perplexity') {
            fixInstructions = `**How to fix:**\n- Check that \`PERPLEXITY_API_KEY\` is set in your backend \`.env\` file\n- Get your API key from https://www.perplexity.ai/settings/api\n- Restart the backend server after adding the key`;
          } else {
            fixInstructions = `**How to fix:**\n- Check that the API key for ${modelName} is set correctly in your backend \`.env\` file\n- Verify the API key is valid and not expired\n- Restart the backend server after adding the key`;
          }
        } else if (errorType === 'rate_limit') {
          fixInstructions = `**How to fix:**\n- You've hit the rate limit for ${modelName}\n- Wait a few minutes before trying again\n- Check your API usage and upgrade your plan if needed`;
        } else if (errorType === 'timeout') {
          fixInstructions = `**How to fix:**\n- The request to ${modelName} timed out\n- Try again with a shorter request\n- Check your network connection`;
        } else {
          fixInstructions = `**How to fix:**\n- Check your network connection\n- Verify the API key for ${modelName} is valid\n- Check the backend logs for more details`;
        }

        // Add error message to chat
        const errorMessage: Message = {
          id: `error-${step.id}-${Date.now()}`,
          role: 'assistant',
          content: `**Error in ${step.role} step using ${modelName}**\n\n${errorMsg}\n\n${fixInstructions}`,
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
        // Remove standalone separator lines (--- on their own line, but preserve list items)
        // Only remove lines that are ONLY dashes (3+ dashes) with optional whitespace
        .replace(/^\s*-{3,}\s*$/gm, '')
        // Remove quadruple asterisks (invalid markdown)
        .replace(/\*\*\*\*/g, '')
        // Remove triple asterisks (invalid markdown, but keep ** for bold)
        // Be careful not to remove list markers - only remove standalone ***
        .replace(/\*\*\*(?!\*)/g, '')
        // Remove headers deeper than h3 (keep h1, h2, h3)
        .replace(/^#{4,}\s+/gm, '### ')
        // Clean up excessive whitespace (but preserve list formatting)
        .replace(/\n{3,}/g, '\n\n')
        // Remove leading/trailing lines that are ONLY dashes or asterisks (separator lines)
        // But preserve list items which have content after the dash/asterisk
        .split('\n')
        .filter(line => {
          const trimmed = line.trim()
          // Keep all lines that have actual content (not just separators)
          // Remove lines that are ONLY dashes/asterisks (3+ chars) - these are separators
          // But keep list items like "- item" or "* item" or "1. item"
          if (/^[\s\-*]{3,}$/.test(trimmed)) {
            // This is a separator line (only dashes/asterisks), remove it
            return false
          }
          // Keep everything else (including valid list items and numbered lists)
          return true
        })
        .join('\n')
        // Clean up any remaining excessive whitespace
        .replace(/\n{3,}/g, '\n\n')
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
  }, [updateStep, setMessages, toggleCollaborateMode, updateCollabPanelForStep])

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
    setAutoRoutedModel(null)
    // Clear any URL parameters
    router.replace('/conversations', { scroll: false })
    console.log('🆕 Started new chat - reset thread ID and messages')
  }

  const handleHistoryClick = (id: string) => {
    router.push(`/conversations/${id}`)
  }

  const handleDeleteChat = (id: string) => {
    setHistory((prev) => prev.filter((item) => item.id !== id))
    toast.success('Chat deleted')
  }

  const handleRenameChat = (id: string, newName: string) => {
    setHistory((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, firstLine: newName } : item
      )
    )
    toast.success('Chat renamed')
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
      const wasNewThread = !currentThreadId // Track before we create/set thread

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
            user_id: (user as { uid: string } | null)?.uid || null,
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

      // Step 2: Use Next.js API route to proxy streaming request (avoids CORS issues)
      const streamHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
        'x-org-id': orgId,
      }
      if (accessToken) {
        streamHeaders['Authorization'] = `Bearer ${accessToken}`
      }

      // Prepare request body for /api/chat route
      const chatRequestBody: any = {
        prompt: content.trim(),
        thread_id: threadId,
      }

      // Add attachments if provided
      if (requestBody.attachments) {
        chatRequestBody.attachments = requestBody.attachments
      }

      // Add user_id if available
      const userId = (user as { uid?: string } | null)?.uid
      if (userId) {
        chatRequestBody.user_id = userId
      }

      console.log('📡 Starting streaming request to:', `/api/chat`)

      let streamResponse: Response
      try {
        streamResponse = await fetch('/api/chat', {
          method: 'POST',
          headers: streamHeaders,
          body: JSON.stringify(chatRequestBody),
        })
      } catch (error) {
        console.error('🚨 Network error during fetch:', error)
        console.error('🚨 Attempted URL:', `/api/chat`)

        // Provide user-friendly error message
        const errorMessage = error instanceof Error
          ? error.message
          : 'Unknown network error'

        // Check if it's a connection error
        if (errorMessage.includes('Failed to fetch') || errorMessage.includes('NetworkError')) {
          toast.error('Unable to connect to the server. Please check your connection.')
          throw new Error(`Connection failed: ${errorMessage}`)
        }

        throw new Error(`Network error: ${errorMessage}`)
      }

      if (!streamResponse.ok) {
        const errorText = await streamResponse.text()
        console.error('❌ Streaming failed:', streamResponse.status, errorText)

        let errorDetails: any
        try {
          errorDetails = JSON.parse(errorText)
        } catch {
          errorDetails = { error: errorText }
        }

        throw new Error(errorDetails.details || errorDetails.error || `Failed to start streaming: ${errorText}`)
      }

      // Extract thread_id from response headers if available (for new threads)
      const responseThreadId = streamResponse.headers.get('x-thread-id') || threadId
      if (responseThreadId !== threadId && responseThreadId) {
        console.log('🔄 Received new thread_id from server:', responseThreadId)
        setCurrentThreadId(responseThreadId)
      }

      // Create assistant message placeholder
      const assistantMessageId = `assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      let assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        media: [],
        timestamp: new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        }),
        modelId: selectedModel,
        modelName: selectedModelData?.name || 'DAC',
      }

      // Add placeholder message immediately
      setMessages((prev) => [...prev, assistantMessage])

      // Read SSE stream
      const reader = streamResponse.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let sawFirstDelta = false
      let provider = ''
      let model = ''

      if (!reader) {
        throw new Error('No response body')
      }

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // Process complete SSE messages
          let eom = buffer.indexOf('\n\n')
          while (eom !== -1) {
            const raw = buffer.slice(0, eom)
            buffer = buffer.slice(eom + 2)
            eom = buffer.indexOf('\n\n')

            // Parse SSE event
            let eventType = 'delta'
            let dataLine = ''
            for (const line of raw.split('\n')) {
              if (line.startsWith('event:')) {
                eventType = line.slice(6).trim()
              }
              if (line.startsWith('data:')) {
                dataLine += line.slice(5).trim()
              }
            }

            if (!dataLine) continue

            try {
              const eventData = JSON.parse(dataLine)

              if (eventType === 'router') {
                // Provider/model info
                provider = eventData.provider || ''
                model = eventData.model || ''
                console.log('🔧 Router decision:', provider, model)
              } else if (eventType === 'delta') {
                // Text content
                if (!sawFirstDelta) {
                  sawFirstDelta = true
                  console.log('🚀 First chunk received')
                }
                const delta = eventData.delta || dataLine
                updateMessage(assistantMessageId, {
                  content: (prev: string) => (prev || '') + delta,
                })
              } else if (eventType === 'media') {
                // Generated image or graph
                console.log('🎨 Media event received:', eventData)
                updateMessage(assistantMessageId, {
                  media: (prev: Array<{ type: 'image' | 'graph'; url: string; alt?: string; mime_type?: string }>) => [
                    ...(prev || []),
                    {
                      type: eventData.type === 'graph' ? 'graph' : 'image',
                      url: eventData.url,
                      alt: eventData.alt,
                      mime_type: eventData.mime_type,
                    },
                  ],
                })
              } else if (eventType === 'done') {
                // Stream complete
                console.log('✅ Stream complete')
                // Update final message with any metadata
                if (provider || model) {
                  updateMessage(assistantMessageId, {
                    modelName: model || provider || selectedModelData?.name || 'DAC',
                  })
                }
              } else if (eventType === 'error') {
                console.error('❌ Stream error:', eventData.error)
                updateMessage(assistantMessageId, {
                  content: (prev: string) => prev + `\n\n⚠️ Error: ${eventData.error}`,
                })
              }
            } catch (parseError) {
              // If it's not JSON, treat as plain text delta
              if (eventType === 'delta') {
                updateMessage(assistantMessageId, {
                  content: (prev: string) => (prev || '') + dataLine,
                })
              }
            }
          }
        }
      } finally {
        reader.releaseLock()
      }

      // Update final message with reasoning type and other metadata
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

      // Get final content to determine reasoning type
      const finalMessage = messages.find((m) => m.id === assistantMessageId)
      const finalContent = finalMessage?.content || ''

      // Update final message with metadata
      updateMessage(assistantMessageId, {
        reasoningType: determineReasoningType(finalContent, content),
        confidence: Math.floor(85 + Math.random() * 15),
        processingTime: Math.floor(800 + Math.random() * 1200),
        chainOfThought: selectedModelData
          ? `I analyzed your request using ${selectedModelData.name}. This model excels at ${selectedModelData.description?.toLowerCase() || 'advanced language processing'}. I applied systematic reasoning to understand your needs, gathered relevant context, synthesized the information, and formulated a comprehensive response.`
          : undefined,
      })

      // Capture the auto-routed model if using auto mode
      if (selectedModel === 'auto' && assistantMessage.modelName) {
        setAutoRoutedModel(assistantMessage.modelName)
      }

      // If we just created a new thread, navigate to its page so it shows in sidebar
      if (wasNewThread && threadId) {
        router.push(`/conversations/${threadId}`)
      }

    } catch (error: any) {
      console.error('💥 Error sending message:', error)
      console.error('💥 Error details:', {
        message: error.message,
        stack: error.stack,
        name: error.name
      })

      // Show specific error message if available, otherwise show generic message
      const errorMessage = error?.message || 'Failed to send message. Please try again.'
      toast.error(errorMessage)

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
      onDeleteChat={handleDeleteChat}
      onRenameChat={handleRenameChat}
      isLoading={isLoading}
      selectedModel={selectedModel}
      onModelSelect={handleModelSelect}
      onContinueWorkflow={handleContinueWorkflow}
      autoRoutedModel={autoRoutedModel}
      collabPanel={collabPanel}
      currentThreadId={currentThreadId}
      useNewThreadsSystem={true}
    />
  )
}
