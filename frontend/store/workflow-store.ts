'use client'

import { create } from 'zustand';

export type WorkflowRole = "analyst" | "researcher" | "creator" | "critic" | "reviews" | "director" | "synthesizer";
export type WorkflowModel = "gpt" | "gemini" | "perplexity" | "kimi" | "multi";
export type WorkflowMode = "manual" | "auto";
export type WorkflowStatus = "pending" | "running" | "awaiting_user" | "done" | "error" | "cancelled";

export interface WorkflowStep {
  id: string
  role: WorkflowRole
  model: WorkflowModel
  mode: WorkflowMode
  status: WorkflowStatus
  inputContext: string
  outputDraft?: string
  outputFinal?: string
  error?: {
    message: string
    provider?: string
    type?: "config" | "network" | "rate_limit" | "timeout" | "unknown"
  }
  metadata?: {
    isMock?: boolean
    providerName?: string
    processing_time_ms?: number
    latency_ms?: number
  }
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
