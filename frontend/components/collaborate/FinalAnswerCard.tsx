"use client";

import React from "react";
import { FinalAnswer } from "@/lib/collaborate-types";
import { getConfidenceBadgeColor, getConfidenceEmoji } from "@/lib/collaborate-types";
import { EnhancedMessageContent } from "@/components/enhanced-message-content";

interface FinalAnswerCardProps {
  finalAnswer: FinalAnswer;
  meta?: {
    models_used?: any[];
    num_external_reviews?: number;
    total_latency_ms?: number;
  };
}

export function FinalAnswerCard({ finalAnswer, meta }: FinalAnswerCardProps) {
  return (
    <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden shadow-sm">
      {/* Header with confidence badge */}
      <div className="border-b border-slate-200 dark:border-slate-800 bg-gradient-to-r from-slate-50 to-blue-50 dark:from-slate-800/50 dark:to-blue-900/20 px-6 py-4 flex items-start justify-between gap-4">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-50 mb-1">
            ✅ Synthesized Answer
          </h3>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            {finalAnswer.synthesized_by?.display_name || "Multi-model synthesis"}
          </p>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-semibold whitespace-nowrap flex-shrink-0 ${getConfidenceBadgeColor(finalAnswer.confidence)}`}>
          {getConfidenceEmoji(finalAnswer.confidence)} {finalAnswer.confidence.charAt(0).toUpperCase() + finalAnswer.confidence.slice(1)}
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-4">
        <div className="text-slate-900 dark:text-slate-50">
          <EnhancedMessageContent
            content={finalAnswer.content}
            role="assistant"
          />
        </div>
      </div>

      {/* Footer with metadata */}
      {meta && (
        <div className="border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30 px-6 py-3 flex flex-wrap items-center gap-4 text-xs text-slate-600 dark:text-slate-400">
          {meta.models_used && meta.models_used.length > 0 && (
            <div className="flex items-center gap-1">
              <span className="font-medium">Models:</span>
              <span>{meta.models_used.length} used</span>
            </div>
          )}
          {meta.num_external_reviews && (
            <div className="flex items-center gap-1">
              <span className="font-medium">Reviews:</span>
              <span>{meta.num_external_reviews} expert evaluations</span>
            </div>
          )}
          {meta.total_latency_ms && (
            <div className="flex items-center gap-1">
              <span className="font-medium">Time:</span>
              <span>{(meta.total_latency_ms / 1000).toFixed(1)}s</span>
            </div>
          )}
        </div>
      )}

      {/* Explanation if available */}
      {finalAnswer.explanation && (
        <div className="border-t border-slate-200 dark:border-slate-800 px-6 py-3 bg-blue-50 dark:bg-blue-900/10">
          <p className="text-xs text-slate-700 dark:text-slate-300 italic">
            💡 {finalAnswer.explanation}
          </p>
        </div>
      )}
    </div>
  );
}
