"use client";

import React, { useState } from "react";
import { CollaborateResponse } from "@/lib/collaborate-types";

interface DetailedAnalysisPanelProps {
  data: CollaborateResponse;
}

export function DetailedAnalysisPanel({ data }: DetailedAnalysisPanelProps) {
  const [activeTab, setActiveTab] = useState<"pipeline" | "reviews" | "metadata">("pipeline");

  return (
    <div className="w-full space-y-4">
      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-700">
        <TabButton
          active={activeTab === "pipeline"}
          onClick={() => setActiveTab("pipeline")}
          label="🔄 Internal Pipeline"
          count={data.internal_pipeline.stages.length}
        />
        <TabButton
          active={activeTab === "reviews"}
          onClick={() => setActiveTab("reviews")}
          label="👥 External Reviews"
          count={data.external_reviews.length}
        />
        <TabButton
          active={activeTab === "metadata"}
          onClick={() => setActiveTab("metadata")}
          label="📋 Metadata"
        />
      </div>

      {/* Tab Content */}
      <div className="pt-4">
        {activeTab === "pipeline" && <PipelineTab data={data} />}
        {activeTab === "reviews" && <ReviewsTab data={data} />}
        {activeTab === "metadata" && <MetadataTab data={data} />}
      </div>
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  label: string;
  count?: number;
}

function TabButton({ active, onClick, label, count }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
        active
          ? "border-blue-600 dark:border-blue-400 text-blue-600 dark:text-blue-400"
          : "border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
      }`}
    >
      {label}
      {count !== undefined && (
        <span className="ml-2 inline-flex items-center justify-center h-5 w-5 rounded-full bg-slate-200 dark:bg-slate-700 text-xs font-semibold">
          {count}
        </span>
      )}
    </button>
  );
}

function PipelineTab({ data }: { data: CollaborateResponse }) {
  return (
    <div className="space-y-4">
      <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Internal Pipeline Timeline</h4>

      {/* Stages */}
      <div className="space-y-4">
        {data.internal_pipeline.stages.map((stage, idx) => (
          <div key={idx} className="border border-slate-200 dark:border-slate-700 rounded-lg p-4">
            {/* Stage Header */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm font-semibold">
                    {idx + 1}
                  </span>
                  <h5 className="font-semibold text-slate-900 dark:text-slate-50 capitalize">
                    {stage.role.replace(/_/g, " ")}
                  </h5>
                </div>
                <div className="mt-1 text-xs text-slate-600 dark:text-slate-400 ml-8">
                  {stage.model_info.display_name} • {stage.latency_ms}ms
                  {stage.tokens_output && ` • ${stage.tokens_input || 0}→${stage.tokens_output} tokens`}
                </div>
              </div>
              <span
                className={`px-2 py-1 rounded text-xs font-semibold ${
                  stage.status === "completed"
                    ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                    : stage.status === "failed"
                      ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                      : "bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300"
                }`}
              >
                {stage.status.charAt(0).toUpperCase() + stage.status.slice(1)}
              </span>
            </div>

            {/* Stage Content */}
            <div className="bg-slate-50 dark:bg-slate-800/50 rounded p-3 text-sm text-slate-700 dark:text-slate-300 max-h-48 overflow-y-auto">
              <p className="whitespace-pre-wrap font-mono text-xs">{stage.content.substring(0, 500)}</p>
              {stage.content.length > 500 && (
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">[... {stage.content.length - 500} more characters]</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Compressed Report */}
      {data.internal_pipeline.compressed_report && (
        <div className="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
          <h5 className="text-sm font-semibold text-slate-900 dark:text-slate-50 mb-2">
            📄 Compressed Internal Report
          </h5>
          <div className="bg-slate-50 dark:bg-slate-800/50 rounded p-4 text-sm text-slate-700 dark:text-slate-300 max-h-64 overflow-y-auto">
            <p>{data.internal_pipeline.compressed_report}</p>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
            This report was sent to external reviewers for evaluation
          </p>
        </div>
      )}
    </div>
  );
}

function ReviewsTab({ data }: { data: CollaborateResponse }) {
  return (
    <div className="space-y-4">
      <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">External Reviews</h4>

      {/* Individual Reviews */}
      <div className="space-y-4">
        {data.external_reviews.map((review, idx) => (
          <div key={idx} className="border border-slate-200 dark:border-slate-700 rounded-lg p-4">
            {/* Review Header */}
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h5 className="font-semibold text-slate-900 dark:text-slate-50">
                    Expert {String.fromCharCode(65 + idx)}
                  </h5>
                  <span className="text-xs text-slate-600 dark:text-slate-400">{review.source}</span>
                </div>
                {review.latency_ms && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {review.latency_ms}ms {review.tokens_used && `• ${review.tokens_used} tokens`}
                  </p>
                )}
              </div>
              <StanceBadge stance={review.stance} />
            </div>

            {/* Review Content */}
            <div className="space-y-3">
              {review.issues && review.issues.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-red-600 dark:text-red-400 mb-1">⚠️ Issues:</p>
                  <ul className="text-sm text-slate-700 dark:text-slate-300 space-y-1 ml-4">
                    {review.issues.map((issue, i) => (
                      <li key={i} className="list-disc">
                        {issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {review.missing && review.missing.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-yellow-600 dark:text-yellow-400 mb-1">📝 Missing Points:</p>
                  <ul className="text-sm text-slate-700 dark:text-slate-300 space-y-1 ml-4">
                    {review.missing.map((item, i) => (
                      <li key={i} className="list-disc">
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {review.suggestions && review.suggestions.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-1">💡 Suggestions:</p>
                  <ul className="text-sm text-slate-700 dark:text-slate-300 space-y-1 ml-4">
                    {review.suggestions.map((suggestion, i) => (
                      <li key={i} className="list-disc">
                        {suggestion}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {review.comment && (
                <div className="bg-slate-50 dark:bg-slate-800/50 rounded p-3">
                  <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Overall Comment:</p>
                  <p className="text-sm text-slate-700 dark:text-slate-300">{review.comment}</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Review Summary Statistics */}
      <div className="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
        <h5 className="text-sm font-semibold text-slate-900 dark:text-slate-50 mb-3">📊 Review Statistics</h5>
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            label="Average Stance Agreement"
            value={`${Math.round(
              (data.external_reviews.filter((r) => r.stance === "agree").length / data.external_reviews.length) * 100
            )}%`}
          />
          <StatCard
            label="Total Reviewers"
            value={data.external_reviews.length.toString()}
          />
          <StatCard
            label="Total Latency"
            value={`${(
              (data.external_reviews.reduce((sum, r) => sum + (r.latency_ms || 0), 0) / 1000).toFixed(1)
            )}s`}
          />
          <StatCard
            label="Total Tokens"
            value={data.external_reviews.reduce((sum, r) => sum + (r.tokens_used || 0), 0).toString()}
          />
        </div>
      </div>
    </div>
  );
}

function MetadataTab({ data }: { data: CollaborateResponse }) {
  return (
    <div className="space-y-4">
      <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Collaboration Metadata</h4>

      <div className="grid grid-cols-2 gap-3">
        <MetadataItem label="Run ID" value={data.meta.run_id} copyable />
        <MetadataItem label="Mode" value={data.meta.mode} />
        <MetadataItem label="Started At" value={new Date(data.meta.started_at).toLocaleTimeString()} />
        <MetadataItem label="Finished At" value={new Date(data.meta.finished_at).toLocaleTimeString()} />
        <MetadataItem label="Total Latency" value={`${(data.meta.total_latency_ms / 1000).toFixed(2)}s`} />
        <MetadataItem label="Total Tokens" value={data.meta.total_tokens.toString()} />
      </div>

      {/* Models Involved */}
      <div className="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
        <h5 className="text-sm font-semibold text-slate-900 dark:text-slate-50 mb-3">Models Involved</h5>
        <div className="space-y-2">
          {data.meta.models_used.map((model, idx) => (
            <div key={idx} className="flex items-start gap-2 p-2 bg-slate-50 dark:bg-slate-800/50 rounded">
              <span className="h-2 w-2 rounded-full bg-blue-600 dark:bg-blue-400 mt-1.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-900 dark:text-slate-50">{model.display_name}</p>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  {model.provider} • {model.model}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface MetadataItemProps {
  label: string;
  value: string;
  copyable?: boolean;
}

function MetadataItem({ label, value, copyable }: MetadataItemProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-slate-50 dark:bg-slate-800/50 rounded p-3 text-sm">
      <p className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">{label}</p>
      <div className="flex items-center justify-between gap-2">
        <p className="text-slate-900 dark:text-slate-50 font-mono text-xs break-all">{value}</p>
        {copyable && (
          <button
            onClick={handleCopy}
            className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-500 dark:hover:text-slate-300 whitespace-nowrap"
          >
            {copied ? "✓ Copied" : "Copy"}
          </button>
        )}
      </div>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="bg-slate-50 dark:bg-slate-800/50 rounded p-3">
      <p className="text-xs text-slate-600 dark:text-slate-400 font-medium">{label}</p>
      <p className="text-lg font-bold text-slate-900 dark:text-slate-50 mt-1">{value}</p>
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
