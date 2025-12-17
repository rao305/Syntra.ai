"use client";

import React, { useState, useEffect } from 'react';

interface LoadingStateProps {
  mode: 'auto' | 'collaborate' | 'single';
  currentStage?: string;
  currentModel?: string;
  stagesCompleted?: number;
  totalStages?: number;
  elapsedMs?: number;
  status?: 'selecting' | 'processing' | 'generating' | 'synthesizing';
}

// Thinking messages that rotate
const THINKING_MESSAGES = [
  "Analyzing your request...",
  "Gathering context...",
  "Formulating response...",
  "Processing information...",
  "Thinking deeply...",
  "Connecting ideas...",
];

// Model-specific messages
const MODEL_MESSAGES: Record<string, string[]> = {
  'gpt-4o': ["GPT-4o is reasoning...", "Analyzing with GPT-4o..."],
  'gemini': ["Gemini is processing...", "Consulting Gemini..."],
  'claude': ["Claude is thinking...", "Claude is composing..."],
  'perplexity': ["Searching the web...", "Gathering sources..."],
};

// Stage labels for collaboration mode
const STAGE_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  'analyst': { label: 'Analyzing Problem', icon: '🔍', color: 'text-blue-400' },
  'researcher': { label: 'Researching', icon: '📚', color: 'text-green-400' },
  'creator': { label: 'Drafting Solution', icon: '✏️', color: 'text-yellow-400' },
  'critic': { label: 'Reviewing', icon: '🎯', color: 'text-orange-400' },
  'council': { label: 'Council Deliberating', icon: '⚖️', color: 'text-purple-400' },
  'synthesizer': { label: 'Synthesizing', icon: '🧬', color: 'text-pink-400' },
  'judge': { label: 'Final Review', icon: '✅', color: 'text-emerald-400' },
};

export const LoadingState: React.FC<LoadingStateProps> = ({
  mode = 'auto',
  currentStage,
  currentModel,
  stagesCompleted = 0,
  totalStages = 6,
  elapsedMs = 0,
  status = 'processing',
}) => {
  const [thinkingIndex, setThinkingIndex] = useState(0);
  const [dots, setDots] = useState('');

  // Rotate thinking messages
  useEffect(() => {
    const interval = setInterval(() => {
      setThinkingIndex((prev) => (prev + 1) % THINKING_MESSAGES.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  // Animate dots
  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? '' : prev + '.'));
    }, 400);
    return () => clearInterval(interval);
  }, []);

  // Format elapsed time
  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  // Get model icon
  const getModelIcon = (model: string) => {
    const lower = model.toLowerCase();
    if (lower.includes('gpt')) return '🟢';
    if (lower.includes('gemini')) return '🔵';
    if (lower.includes('claude')) return '🟣';
    if (lower.includes('perplexity') || lower.includes('sonar')) return '🟠';
    return '🤖';
  };

  // === COLLABORATION MODE LOADING ===
  if (mode === 'collaborate') {
    const stageInfo = currentStage ? STAGE_LABELS[currentStage] : null;
    const progress = (stagesCompleted / totalStages) * 100;

    return (
      <div className="loading-state-collaboration p-4 rounded-xl bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 max-w-lg">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <div className="relative">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <span className="text-sm">🧠</span>
            </div>
            <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-gray-900 animate-pulse" />
          </div>
          <div>
            <div className="text-sm font-medium text-gray-200">
              Syntra Collaboration
            </div>
            <div className="text-xs text-gray-500">
              Multi-model synthesis in progress
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Stage {stagesCompleted + 1} of {totalStages}</span>
            <span>{formatTime(elapsedMs)}</span>
          </div>
          <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.max(progress, 5)}%` }}
            />
          </div>
        </div>

        {/* Current Stage */}
        {stageInfo && (
          <div className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg mb-3">
            <div className="text-2xl animate-bounce-slow">
              {stageInfo.icon}
            </div>
            <div className="flex-1">
              <div className={`text-sm font-medium ${stageInfo.color}`}>
                {stageInfo.label}{dots}
              </div>
              {currentModel && (
                <div className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                  {getModelIcon(currentModel)} {currentModel}
                </div>
              )}
            </div>
            <div className="flex gap-1">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse delay-100" />
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse delay-200" />
            </div>
          </div>
        )}

        {/* Stage Pipeline Visualization */}
        <div className="flex items-center justify-between px-2">
          {Object.entries(STAGE_LABELS).slice(0, totalStages).map(([key, stage], index) => {
            const isComplete = index < stagesCompleted;
            const isCurrent = key === currentStage;
            
            return (
              <React.Fragment key={key}>
                <div className="flex flex-col items-center">
                  <div
                    className={`
                      w-6 h-6 rounded-full flex items-center justify-center text-xs
                      transition-all duration-300
                      ${isComplete 
                        ? 'bg-green-500/20 text-green-400 ring-2 ring-green-500/50' 
                        :  isCurrent 
                          ? 'bg-blue-500/20 text-blue-400 ring-2 ring-blue-500/50 animate-pulse' 
                          : 'bg-gray-700/50 text-gray-600'}
                    `}
                    title={stage.label}
                  >
                    {isComplete ?  '✓' : stage.icon}
                  </div>
                </div>
                {index < totalStages - 1 && (
                  <div
                    className={`
                      flex-1 h-0.5 mx-1 rounded transition-colors duration-300
                      ${index < stagesCompleted ? 'bg-green-500/50' : 'bg-gray-700'}
                    `}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    );
  }

  // === AUTO/SINGLE MODE LOADING ===
  return (
    <div className="loading-state-simple flex items-start gap-3 p-4">
      {/* Animated Logo/Avatar */}
      <div className="relative">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1">
        {/* Status Message */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-300">
            {status === 'selecting' && 'Selecting best model'}
            {status === 'processing' && THINKING_MESSAGES[thinkingIndex]}
            {status === 'generating' && 'Generating response'}
            {status === 'synthesizing' && 'Finalizing'}
            {dots}
          </span>
        </div>

        {/* Model Info */}
        {currentModel && (
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className="text-sm">{getModelIcon(currentModel)}</span>
            <span className="text-xs text-gray-500">{currentModel}</span>
          </div>
        )}

        {/* Typing Indicator */}
        <div className="flex items-center gap-1 mt-3">
          <div className="typing-indicator flex gap-1">
            <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          {elapsedMs > 0 && (
            <span className="text-xs text-gray-600 ml-2">
              {formatTime(elapsedMs)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoadingState;
