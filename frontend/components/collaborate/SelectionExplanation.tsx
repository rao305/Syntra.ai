"use client";

import React from "react";
import { CollaborateResponse, calculateQualityMetrics, getStanceDistribution } from "@/lib/collaborate-types";

interface SelectionExplanationProps {
  data: CollaborateResponse;
}

export function SelectionExplanation({ data }: SelectionExplanationProps) {
  const metrics = calculateQualityMetrics(data);
  const stanceDistribution = getStanceDistribution(data.external_reviews);

  const getConfidenceExplanation = (confidence: string): string => {
    switch (confidence) {
      case "high":
        return "Strong council agreement and high quality metrics indicate a reliable answer";
      case "medium":
        return "Moderate agreement with some reviewer concerns, but overall solid response";
      case "low":
        return "Mixed feedback and flagged issues require careful review";
      default:
        return "Confidence level assessment in progress";
    }
  };

  return (
    <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden shadow-sm">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 px-6 py-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">🎯</span>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-50">
            How This Answer Was Selected
          </h3>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-6 space-y-6">
        {/* Council Review Results */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">👥</span>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">
              Council Review Results ({data.external_reviews.length} Expert Judges)
            </h4>
          </div>

          <div className="space-y-2 mb-3">
            {data.external_reviews.map((review, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-sm"
              >
                <span className="text-slate-700 dark:text-slate-300">
                  Expert {String.fromCharCode(65 + idx)} ({review.source})
                </span>
                <StanceBadge stance={review.stance} />
              </div>
            ))}
          </div>

          {/* Summary badges */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 font-medium">
              ✓ {stanceDistribution.agree_count} Agree
            </span>
            {stanceDistribution.mixed_count > 0 && (
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 font-medium">
                ◆ {stanceDistribution.mixed_count} Mixed
              </span>
            )}
            {stanceDistribution.disagree_count > 0 && (
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-medium">
                ✗ {stanceDistribution.disagree_count} Disagree
              </span>
            )}
          </div>
        </div>

        {/* Quality Metrics */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">📊</span>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Quality Metrics</h4>
          </div>

          <div className="space-y-2 mb-4">
            <MetricBar label="Synthesis Quality" value={metrics.synthesis_quality} weight="(40%)" />
            <MetricBar label="Content Depth" value={metrics.content_depth} weight="(25%)" />
            <MetricBar label="Innovation" value={metrics.innovation} weight="(20%)" />
            <MetricBar label="Clarity Score" value={metrics.clarity} weight="(15%)" />
          </div>

          {/* Overall Score */}
          <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-slate-900 dark:text-slate-50">Overall Quality Score</span>
              <span className="text-lg font-bold text-blue-600 dark:text-blue-400">{metrics.overall_score}%</span>
            </div>
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-400 dark:to-blue-500 transition-all duration-300"
                style={{ width: `${metrics.overall_score}%` }}
              />
            </div>
          </div>
        </div>

        {/* Selection Criteria Met */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">✅</span>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Selection Criteria Met</h4>
          </div>

          <div className="space-y-2 text-sm">
            <CriteriaItem
              label="Anonymous Quality-Based Selection"
              met={true}
              description="Answer selected by quality metrics, not model identity"
            />
            <CriteriaItem
              label="Synthesis Quality"
              met={metrics.synthesis_quality >= 70}
              description={`Score: ${metrics.synthesis_quality}%`}
            />
            <CriteriaItem
              label="Content Depth"
              met={metrics.content_depth >= 60}
              description={`Score: ${metrics.content_depth}%`}
            />
            <CriteriaItem
              label="Innovation Level"
              met={metrics.innovation >= 60}
              description={`Score: ${metrics.innovation}%`}
            />
            <CriteriaItem label="Clarity Score" met={metrics.clarity >= 60} description={`Score: ${metrics.clarity}%`} />
          </div>
        </div>

        {/* Confidence Level */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">🔒</span>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Confidence Level</h4>
          </div>

          <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4 border-l-4 border-blue-500">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg font-bold text-blue-600 dark:text-blue-400">
                {data.final_answer.confidence.toUpperCase()}
              </span>
              <span className="text-2xl">✓</span>
            </div>
            <p className="text-sm text-slate-700 dark:text-slate-300">
              {getConfidenceExplanation(data.final_answer.confidence)}
            </p>
          </div>
        </div>

        {/* Transparency Note */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 text-sm text-slate-700 dark:text-slate-300 border border-blue-200 dark:border-blue-800">
          <p className="font-medium text-blue-900 dark:text-blue-200 mb-1">💡 Transparency Note</p>
          <p>
            This answer was created by synthesizing inputs from {data.meta.models_used.length}+ AI models. Each expert
            judge reviewed anonymously, without model identity bias. The final answer was selected based on quality
            metrics alone.
          </p>
        </div>
      </div>
    </div>
  );
}

function StanceBadge({ stance }: { stance: string }) {
  const stanceConfig = {
    agree: { emoji: "✓", color: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300" },
    disagree: { emoji: "✗", color: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300" },
    mixed: { emoji: "◆", color: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300" },
    unknown: { emoji: "?", color: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300" },
  };

  const config = stanceConfig[stance as keyof typeof stanceConfig] || stanceConfig.unknown;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${config.color}`}>
      <span>{config.emoji}</span>
      <span>{stance.charAt(0).toUpperCase() + stance.slice(1)}</span>
    </span>
  );
}

interface MetricBarProps {
  label: string;
  value: number;
  weight: string;
}

function MetricBar({ label, value, weight }: MetricBarProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
          {label} <span className="text-slate-500 dark:text-slate-400">{weight}</span>
        </span>
        <span className="text-xs font-bold text-slate-900 dark:text-slate-50">{value}%</span>
      </div>
      <div className="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-slate-400 to-slate-500 dark:from-slate-500 dark:to-slate-600"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

interface CriteriaItemProps {
  label: string;
  met: boolean;
  description: string;
}

function CriteriaItem({ label, met, description }: CriteriaItemProps) {
  return (
    <div className="flex items-start gap-2 p-2 rounded bg-slate-50 dark:bg-slate-800/50">
      <span className={`mt-0.5 text-lg flex-shrink-0 ${met ? "text-green-600 dark:text-green-400" : "text-gray-400"}`}>
        {met ? "✓" : "○"}
      </span>
      <div className="flex-1">
        <div className="font-medium text-slate-900 dark:text-slate-50">{label}</div>
        <div className="text-xs text-slate-600 dark:text-slate-400">{description}</div>
      </div>
    </div>
  );
}
