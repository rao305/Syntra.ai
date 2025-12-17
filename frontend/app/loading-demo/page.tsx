"use client"

import { LoadingState } from '@/components/LoadingState'
import { SimpleLoadingState } from '@/components/SimpleLoadingState'
import { SkeletonResponse } from '@/components/SkeletonResponse'
import { useState, useEffect } from 'react'

export default function LoadingDemoPage() {
  const [elapsedMs, setElapsedMs] = useState(0)
  const [stagesCompleted, setStagesCompleted] = useState(0)
  const [currentStageIndex, setCurrentStageIndex] = useState(0)

  const stages = ['analyst', 'researcher', 'creator', 'critic', 'synthesizer', 'judge']

  // Simulate elapsed time
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedMs((prev) => prev + 100)
    }, 100)
    return () => clearInterval(interval)
  }, [])

  // Simulate stage progression
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStageIndex((prev) => {
        const next = (prev + 1) % stages.length
        if (next === 0) setStagesCompleted(0)
        else setStagesCompleted(next)
        return next
      })
    }, 3000)
    return () => clearInterval(interval)
  }, [stages.length])

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-8">
      <div className="max-w-6xl mx-auto space-y-12">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
            Enhanced Loading States
          </h1>
          <p className="text-gray-400">
            Preview of all loading state components for Syntra AI
          </p>
        </div>

        {/* Collaboration Mode */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-purple-300">
            1. Collaboration Mode (Full)
          </h2>
          <p className="text-sm text-gray-500">
            Shows stage pipeline, progress bar, and current stage with model
          </p>
          <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800">
            <LoadingState
              mode="collaborate"
              currentStage={stages[currentStageIndex]}
              currentModel="GPT-4o"
              stagesCompleted={stagesCompleted}
              totalStages={stages.length}
              elapsedMs={elapsedMs}
              status="processing"
            />
          </div>
        </section>

        {/* Auto Mode */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-blue-300">
            2. Auto Mode (Model Selection)
          </h2>
          <p className="text-sm text-gray-500">
            Shows when auto-selecting the best model
          </p>
          <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800">
            <LoadingState
              mode="auto"
              elapsedMs={elapsedMs}
              status="selecting"
            />
          </div>
        </section>

        {/* Single Model Mode */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-green-300">
            3. Single Model Mode (Generating)
          </h2>
          <p className="text-sm text-gray-500">
            Shows when a specific model is generating
          </p>
          <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800">
            <LoadingState
              mode="auto"
              currentModel="Gemini 2.5 Flash"
              elapsedMs={elapsedMs}
              status="generating"
            />
          </div>
        </section>

        {/* Simple Loading State */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-yellow-300">
            4. Simple Loading State
          </h2>
          <p className="text-sm text-gray-500">
            Lightweight alternative with basic features
          </p>
          <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800">
            <SimpleLoadingState
              model="Claude 3.5"
              isCollaboration={false}
            />
          </div>
        </section>

        {/* Simple Loading State - Collaboration */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-pink-300">
            5. Simple Loading State (Collaboration)
          </h2>
          <p className="text-sm text-gray-500">
            Simple variant with collaboration badge
          </p>
          <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800">
            <SimpleLoadingState
              model="Perplexity Sonar"
              isCollaboration={true}
            />
          </div>
        </section>

        {/* Skeleton Response */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-orange-300">
            6. Skeleton Response
          </h2>
          <p className="text-sm text-gray-500">
            Placeholder showing where response will appear
          </p>
          <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800">
            <SkeletonResponse />
          </div>
        </section>

        {/* Model Icons Reference */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-cyan-300">
            7. Model Icons Reference
          </h2>
          <p className="text-sm text-gray-500">
            Icons automatically shown for different models
          </p>
          <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center space-y-2">
              <div className="text-4xl">🟢</div>
              <div className="text-sm text-gray-400">GPT / OpenAI</div>
            </div>
            <div className="text-center space-y-2">
              <div className="text-4xl">🔵</div>
              <div className="text-sm text-gray-400">Gemini</div>
            </div>
            <div className="text-center space-y-2">
              <div className="text-4xl">🟣</div>
              <div className="text-sm text-gray-400">Claude</div>
            </div>
            <div className="text-center space-y-2">
              <div className="text-4xl">🟠</div>
              <div className="text-sm text-gray-400">Perplexity</div>
            </div>
          </div>
        </section>

        {/* Stage Icons Reference */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-indigo-300">
            8. Collaboration Stages
          </h2>
          <p className="text-sm text-gray-500">
            All collaboration stage icons and labels
          </p>
          <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800 grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <div className="text-2xl">🔍</div>
              <div className="text-sm font-medium text-blue-400">Analyst</div>
              <div className="text-xs text-gray-500">Analyzing Problem</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl">📚</div>
              <div className="text-sm font-medium text-green-400">Researcher</div>
              <div className="text-xs text-gray-500">Researching</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl">✏️</div>
              <div className="text-sm font-medium text-yellow-400">Creator</div>
              <div className="text-xs text-gray-500">Drafting Solution</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl">🎯</div>
              <div className="text-sm font-medium text-orange-400">Critic</div>
              <div className="text-xs text-gray-500">Reviewing</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl">🔬</div>
              <div className="text-sm font-medium text-pink-400">Synthesizer</div>
              <div className="text-xs text-gray-500">Synthesizing</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl">✅</div>
              <div className="text-sm font-medium text-emerald-400">Judge</div>
              <div className="text-xs text-gray-500">Final Review</div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <div className="text-center text-gray-600 text-sm pt-8 border-t border-zinc-800">
          <p>Timer updates every 100ms • Stages rotate every 3s</p>
          <p className="mt-2">
            See <code className="text-purple-400">components/loading/README.md</code> for documentation
          </p>
        </div>
      </div>
    </div>
  )
}
