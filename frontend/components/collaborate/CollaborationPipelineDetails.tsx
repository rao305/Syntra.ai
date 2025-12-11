"use client"

import { cn } from "@/lib/utils"
import { AlertCircle, Brain, CheckCircle2, ChevronDown, ChevronUp, FileText, Users, XCircle } from "lucide-react"
import { useState } from "react"

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

interface CollaborationPipelineDetailsProps {
  stages?: PipelineStage[]
  reviews?: Review[]
  isVisible?: boolean
}

export function CollaborationPipelineDetails({
  stages = [],
  reviews = [],
  isVisible: initialVisible = false
}: CollaborationPipelineDetailsProps) {
  const [isExpanded, setIsExpanded] = useState(initialVisible)
  const [expandedStage, setExpandedStage] = useState<string | null>(null)
  const [expandedReview, setExpandedReview] = useState<string | null>(null)

  if (stages.length === 0 && reviews.length === 0) {
    return null
  }

  return (
    <div className="mt-3 border-t border-zinc-800/50 pt-3">
      {/* Expand/Collapse Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-zinc-400 hover:text-zinc-300 transition-colors w-full"
      >
        {isExpanded ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
        <span className="font-medium">
          {isExpanded ? "Hide" : "Show"} Collaboration Pipeline Details
        </span>
        <span className="text-zinc-500">
          ({stages.length} stages{reviews.length > 0 ? `, ${reviews.length} reviews` : ""})
        </span>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="mt-3 space-y-4">
          {/* Pipeline Stages */}
          {stages.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-zinc-400 mb-2 flex items-center gap-2">
                <Brain className="h-3.5 w-3.5" />
                Internal Pipeline Stages
              </h4>
              <div className="space-y-2">
                {stages.map((stage, idx) => (
                  <div
                    key={stage.id}
                    className="border border-zinc-800/50 rounded-lg overflow-hidden bg-zinc-900/30"
                  >
                    {/* Stage Header */}
                    <button
                      onClick={() => setExpandedStage(expandedStage === stage.id ? null : stage.id)}
                      className="w-full flex items-center justify-between p-2.5 hover:bg-zinc-800/30 transition-colors"
                    >
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <span className="text-xs font-mono text-zinc-500 flex-shrink-0 w-6">
                          {idx + 1}
                        </span>
                        <span className="text-xs font-medium text-zinc-200 capitalize truncate">
                          {stage.label || stage.role}
                        </span>
                        {stage.modelName && (
                          <span className="text-xs text-zinc-500 truncate">
                            • {stage.modelName}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {stage.status === "done" && (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                        )}
                        {stage.status === "failed" && (
                          <XCircle className="h-3.5 w-3.5 text-red-500" />
                        )}
                        {stage.status === "active" && (
                          <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                        )}
                        {stage.latency_ms && (
                          <span className="text-xs text-zinc-500">
                            {stage.latency_ms < 1000 ? `${stage.latency_ms}ms` : `${(stage.latency_ms / 1000).toFixed(1)}s`}
                          </span>
                        )}
                        {expandedStage === stage.id ? (
                          <ChevronUp className="h-3.5 w-3.5 text-zinc-500" />
                        ) : (
                          <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
                        )}
                      </div>
                    </button>

                    {/* Stage Output (Expandable) */}
                    {expandedStage === stage.id && stage.output && (
                      <div className="border-t border-zinc-800/50 p-3 bg-zinc-950/50">
                        <div className="text-xs text-zinc-300 whitespace-pre-wrap font-mono leading-relaxed max-h-64 overflow-y-auto">
                          {stage.output}
                        </div>
                        {stage.tokens && (
                          <div className="mt-2 text-xs text-zinc-500">
                            Tokens: {stage.tokens.input || 0} → {stage.tokens.output || 0}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* External Reviews */}
          {reviews.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-zinc-400 mb-2 flex items-center gap-2">
                <Users className="h-3.5 w-3.5" />
                External Expert Reviews
              </h4>
              <div className="space-y-2">
                {reviews.map((review, idx) => (
                  <div
                    key={review.id}
                    className="border border-zinc-800/50 rounded-lg overflow-hidden bg-zinc-900/30"
                  >
                    {/* Review Header */}
                    <button
                      onClick={() => setExpandedReview(expandedReview === review.id ? null : review.id)}
                      className="w-full flex items-center justify-between p-2.5 hover:bg-zinc-800/30 transition-colors"
                    >
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <span className="text-xs font-medium text-zinc-200 truncate">
                          {review.modelName || review.source || `Review ${idx + 1}`}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <StanceBadge stance={review.stance} />
                        {expandedReview === review.id ? (
                          <ChevronUp className="h-3.5 w-3.5 text-zinc-500" />
                        ) : (
                          <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
                        )}
                      </div>
                    </button>

                    {/* Review Content (Expandable) */}
                    {expandedReview === review.id && (
                      <div className="border-t border-zinc-800/50 p-3 bg-zinc-950/50 space-y-2">
                        {/* Overall Feedback */}
                        {review.feedback && (
                          <div className="text-xs text-zinc-300 whitespace-pre-wrap">
                            {review.feedback}
                          </div>
                        )}
                        {review.content && (
                          <div className="text-xs text-zinc-300 whitespace-pre-wrap">
                            {review.content}
                          </div>
                        )}

                        {/* Issues */}
                        {review.issues && review.issues.length > 0 && (
                          <div>
                            <div className="text-xs font-semibold text-red-400 mb-1 flex items-center gap-1">
                              <AlertCircle className="h-3 w-3" />
                              Issues Found:
                            </div>
                            <ul className="text-xs text-zinc-400 space-y-1 ml-4 list-disc">
                              {review.issues.map((issue, i) => (
                                <li key={i}>{issue}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Suggestions */}
                        {review.suggestions && review.suggestions.length > 0 && (
                          <div>
                            <div className="text-xs font-semibold text-blue-400 mb-1 flex items-center gap-1">
                              <FileText className="h-3 w-3" />
                              Suggestions:
                            </div>
                            <ul className="text-xs text-zinc-400 space-y-1 ml-4 list-disc">
                              {review.suggestions.map((suggestion, i) => (
                                <li key={i}>{suggestion}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StanceBadge({ stance }: { stance: string }) {
  const config = {
    agree: { emoji: "✓", className: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
    disagree: { emoji: "✗", className: "bg-red-500/20 text-red-400 border-red-500/30" },
    mixed: { emoji: "◆", className: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
    unknown: { emoji: "?", className: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30" },
  }

  const badgeConfig = config[stance as keyof typeof config] || config.unknown

  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border",
      badgeConfig.className
    )}>
      <span>{badgeConfig.emoji}</span>
      <span className="capitalize">{stance}</span>
    </span>
  )
}
