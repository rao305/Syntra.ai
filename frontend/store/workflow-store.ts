'use client'

import { create } from 'zustand'

export interface WorkflowStep {
  id: string
  role: 'analyst' | 'researcher' | 'creator' | 'critic' | 'synthesizer'
  status: 'pending' | 'running' | 'awaiting_user' | 'done' | 'error' | 'cancelled'
  model?: string
  inputContext?: string
  outputDraft?: string
  outputFinal?: string
  error?: { message: string; code?: string }
  metadata?: Record<string, any>
}

interface WorkflowState {
  isCollaborateMode: boolean
  mode: 'auto' | 'manual'
  steps: WorkflowStep[]
  toggleCollaborateMode: () => void
  setMode: (mode: 'auto' | 'manual') => void
  setSteps: (steps: WorkflowStep[]) => void
  updateStep: (stepId: string, updates: Partial<WorkflowStep>) => void
  resetWorkflow: () => void
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  isCollaborateMode: false,
  mode: 'manual',
  steps: [],

  toggleCollaborateMode: () =>
    set((state) => ({
      isCollaborateMode: !state.isCollaborateMode,
    })),

  setMode: (mode: 'auto' | 'manual') =>
    set((state) => {
      const updatedSteps = state.steps.map((step) => ({
        ...step,
        status:
          mode === 'auto' && step.status === 'awaiting_user'
            ? 'done'
            : step.status,
      }))
      return { mode, steps: updatedSteps }
    }),

  setSteps: (steps: WorkflowStep[]) =>
    set(() => ({
      steps,
    })),

  updateStep: (stepId: string, updates: Partial<WorkflowStep>) =>
    set((state) => ({
      steps: state.steps.map((step) =>
        step.id === stepId ? { ...step, ...updates } : step
      ),
    })),

  resetWorkflow: () =>
    set(() => ({
      isCollaborateMode: false,
      mode: 'manual',
      steps: [],
    })),
}))
