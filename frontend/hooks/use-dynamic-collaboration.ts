/**
 * React hook for dynamic collaboration
 * 
 * Provides a simple interface to run dynamic collaborations
 * with real-time streaming updates.
 */

import { useCallback, useRef, useState } from 'react'
import { useWorkflowStore } from '@/store/workflow-store'
import {
  runDynamicCollaboration,
  runDynamicCollaborationStream,
  isCollaborationError,
  getCollaborationSummary,
  convertToWorkflowSteps
} from '@/app/actions/collaborate'
import {
  DynamicCollaborateResponse,
  StepResult,
  CollaborationPlan,
  UserPriority,
  StreamEvent
} from '@/lib/orchestrator-types'

interface UseDynamicCollaborationOptions {
  onPlanCreated?: (plan: CollaborationPlan) => void
  onStepStarted?: (stepIndex: number, role: string) => void
  onStepCompleted?: (result: StepResult) => void
  onComplete?: (response: DynamicCollaborateResponse) => void
  onError?: (error: string) => void
}

interface CollaborationState {
  isRunning: boolean
  isPlanning: boolean
  currentStep: number | null
  totalSteps: number
  plan: CollaborationPlan | null
  stepResults: StepResult[]
  finalAnswer: string | null
  error: string | null
  totalTimeMs: number
}

export function useDynamicCollaboration(options: UseDynamicCollaborationOptions = {}) {
  const [state, setState] = useState<CollaborationState>({
    isRunning: false,
    isPlanning: false,
    currentStep: null,
    totalSteps: 0,
    plan: null,
    stepResults: [],
    finalAnswer: null,
    error: null,
    totalTimeMs: 0
  })
  
  const abortControllerRef = useRef<AbortController | null>(null)
  
  // Get settings from store
  const userSettings = useWorkflowStore(state => state.userSettings)
  const setSteps = useWorkflowStore(state => state.setSteps)
  
  /**
   * Run collaboration with streaming updates
   */
  const runWithStreaming = useCallback(async (
    message: string,
    threadId?: string,
    threadContext?: string,
    priority?: UserPriority
  ) => {
    // Reset state
    setState({
      isRunning: true,
      isPlanning: true,
      currentStep: null,
      totalSteps: 0,
      plan: null,
      stepResults: [],
      finalAnswer: null,
      error: null,
      totalTimeMs: 0
    })
    
    const settings = {
      ...userSettings,
      ...(priority && { priority })
    }
    
    try {
      const generator = runDynamicCollaborationStream(
        message,
        threadId,
        threadContext,
        settings
      )
      
      for await (const event of generator) {
        switch (event.type) {
          case 'planning':
            setState(prev => ({ ...prev, isPlanning: true }))
            break
            
          case 'plan_created':
            const plan: CollaborationPlan = {
              pipeline_summary: event.plan.pipeline_summary,
              steps: event.plan.steps.map(s => ({
                step_index: s.step_index,
                role: s.role,
                model_id: s.model_id,
                purpose: s.purpose,
                needs_previous_steps: [],
                estimated_importance: 0.5,
                model_rationale: ''
              })),
              planning_time_ms: event.plan.planning_time_ms
            }
            setState(prev => ({
              ...prev,
              isPlanning: false,
              plan,
              totalSteps: event.plan.steps.length
            }))
            options.onPlanCreated?.(plan)
            break
            
          case 'step_started':
            setState(prev => ({ ...prev, currentStep: event.step_index }))
            options.onStepStarted?.(event.step_index, event.role)
            break
            
          case 'step_completed':
            if (event.success && event.content) {
              const result: StepResult = {
                step_index: event.step_index,
                role: event.role,
                model_id: '',
                model_name: '',
                purpose: '',
                content: event.content || '',
                execution_time_ms: event.execution_time_ms || 0,
                success: event.success,
                error: event.error
              }
              setState(prev => ({
                ...prev,
                stepResults: [...prev.stepResults, result]
              }))
              options.onStepCompleted?.(result)
            }
            break
            
          case 'final_answer':
            setState(prev => ({
              ...prev,
              finalAnswer: event.content,
              isRunning: false
            }))
            break
            
          case 'error':
            setState(prev => ({
              ...prev,
              error: event.message,
              isRunning: false,
              isPlanning: false
            }))
            options.onError?.(event.message)
            break
            
          case 'done':
            setState(prev => ({ ...prev, isRunning: false }))
            break
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isRunning: false,
        isPlanning: false
      }))
      options.onError?.(errorMessage)
    }
  }, [userSettings, options])
  
  /**
   * Run collaboration without streaming (simpler, single response)
   */
  const run = useCallback(async (
    message: string,
    threadId?: string,
    threadContext?: string,
    priority?: UserPriority
  ): Promise<DynamicCollaborateResponse | null> => {
    setState({
      isRunning: true,
      isPlanning: true,
      currentStep: null,
      totalSteps: 0,
      plan: null,
      stepResults: [],
      finalAnswer: null,
      error: null,
      totalTimeMs: 0
    })
    
    const settings = {
      ...userSettings,
      ...(priority && { priority })
    }
    
    try {
      const result = await runDynamicCollaboration(
        message,
        threadId,
        threadContext,
        settings
      )
      
      if (isCollaborationError(result)) {
        setState(prev => ({
          ...prev,
          error: result.error,
          isRunning: false,
          isPlanning: false
        }))
        options.onError?.(result.error)
        return null
      }
      
      // Update state with complete result
      setState({
        isRunning: false,
        isPlanning: false,
        currentStep: result.step_results.length,
        totalSteps: result.plan.steps.length,
        plan: result.plan,
        stepResults: result.step_results,
        finalAnswer: result.final_answer,
        error: null,
        totalTimeMs: result.total_time_ms
      })
      
      // Convert to workflow steps for the existing UI
      const workflowSteps = convertToWorkflowSteps(result)
      setSteps(workflowSteps)
      
      options.onPlanCreated?.(result.plan)
      options.onComplete?.(result)
      
      return result
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isRunning: false,
        isPlanning: false
      }))
      options.onError?.(errorMessage)
      return null
    }
  }, [userSettings, setSteps, options])
  
  /**
   * Cancel an in-progress collaboration
   */
  const cancel = useCallback(() => {
    abortControllerRef.current?.abort()
    setState(prev => ({
      ...prev,
      isRunning: false,
      isPlanning: false
    }))
  }, [])
  
  /**
   * Reset the collaboration state
   */
  const reset = useCallback(() => {
    setState({
      isRunning: false,
      isPlanning: false,
      currentStep: null,
      totalSteps: 0,
      plan: null,
      stepResults: [],
      finalAnswer: null,
      error: null,
      totalTimeMs: 0
    })
  }, [])
  
  /**
   * Get a summary of the current/completed collaboration
   */
  const getSummary = useCallback(() => {
    if (!state.plan) return null
    
    return {
      planSummary: state.plan.pipeline_summary,
      stepsCompleted: `${state.stepResults.length}/${state.totalSteps}`,
      totalTime: state.totalTimeMs > 0 
        ? `${(state.totalTimeMs / 1000).toFixed(1)}s`
        : 'In progress...',
      roles: state.stepResults.map(s => ({
        role: s.role,
        model: s.model_name,
        success: s.success
      }))
    }
  }, [state])
  
  /**
   * Progress percentage (0-100)
   */
  const progress = state.totalSteps > 0
    ? Math.round((state.stepResults.length / state.totalSteps) * 100)
    : (state.isPlanning ? 5 : 0)
  
  return {
    // State
    ...state,
    progress,
    
    // Actions
    run,
    runWithStreaming,
    cancel,
    reset,
    getSummary
  }
}

export type { CollaborationState }












