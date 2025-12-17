"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  AlertCircle,
  Info,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface QualityMetrics {
  substance_score: number;
  completeness_score: number;
  depth_score: number;
  accuracy_score: number;
  overall_score: number;
  quality_gate_passed: boolean;
  query_complexity?: number;
  validation_timestamp?: string;
}

interface QualityScoreCardProps {
  metrics: QualityMetrics;
  showDetails?: boolean;
  compact?: boolean;
}

const getScoreColor = (score: number): string => {
  if (score >= 9) return "text-green-600 dark:text-green-400";
  if (score >= 7) return "text-yellow-600 dark:text-yellow-400";
  if (score >= 5) return "text-orange-600 dark:text-orange-400";
  return "text-red-600 dark:text-red-400";
};

const getScoreBgColor = (score: number): string => {
  if (score >= 9) return "bg-green-500";
  if (score >= 7) return "bg-yellow-500";
  if (score >= 5) return "bg-orange-500";
  return "bg-red-500";
};

const getScoreLabel = (score: number): string => {
  if (score >= 9) return "Excellent";
  if (score >= 7) return "Good";
  if (score >= 5) return "Fair";
  return "Needs Improvement";
};

const getComplexityLabel = (complexity: number): string => {
  const labels = [
    "Simple Factual",
    "Explanatory",
    "Technical Implementation",
    "Research/Analysis",
    "Research-Grade/Expert",
  ];
  return labels[complexity - 1] || "Unknown";
};

const getComplexityBadgeVariant = (
  complexity: number
): "default" | "secondary" | "outline" | "destructive" => {
  if (complexity >= 5) return "destructive";
  if (complexity >= 4) return "default";
  if (complexity >= 3) return "secondary";
  return "outline";
};

const ScoreRow: React.FC<{
  label: string;
  score: number;
  description?: string;
  className?: string;
}> = ({ label, score, description, className = "" }) => {
  const percentage = (score / 10) * 100;
  const colorClass = getScoreColor(score);
  const bgColor = getScoreBgColor(score);

  return (
    <div className={`space-y-1 ${className}`}>
      <div className="flex justify-between items-center text-sm">
        <div className="flex items-center gap-2">
          <span className="font-medium">{label}</span>
          {description && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-3 w-3 text-gray-400 cursor-help" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs text-xs">{description}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        <span className={`font-mono font-semibold ${colorClass}`}>
          {score.toFixed(1)}/10
        </span>
      </div>
      <Progress value={percentage} className="h-2" indicatorClassName={bgColor} />
      <div className="text-xs text-gray-500 text-right">{getScoreLabel(score)}</div>
    </div>
  );
};

const CompactQualityBadge: React.FC<{ metrics: QualityMetrics }> = ({
  metrics,
}) => {
  const { overall_score, quality_gate_passed } = metrics;
  const colorClass = getScoreColor(overall_score);
  const Icon = quality_gate_passed ? CheckCircle2 : AlertCircle;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 cursor-help">
            <Icon
              className={`h-3.5 w-3.5 ${quality_gate_passed ? "text-green-600" : "text-yellow-600"}`}
            />
            <span className={`text-xs font-mono font-semibold ${colorClass}`}>
              {overall_score.toFixed(1)}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1 text-xs">
            <p className="font-semibold">Quality Assessment</p>
            <p>Substance: {metrics.substance_score.toFixed(1)}/10</p>
            <p>Completeness: {metrics.completeness_score.toFixed(1)}/10</p>
            <p>Depth: {metrics.depth_score.toFixed(1)}/10</p>
            <p>Accuracy: {metrics.accuracy_score.toFixed(1)}/10</p>
            <p className="pt-1 border-t">
              Status:{" "}
              {quality_gate_passed ? "✓ Passed" : "⚠ Needs Review"}
            </p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

export const QualityScoreCard: React.FC<QualityScoreCardProps> = ({
  metrics,
  showDetails = true,
  compact = false,
}) => {
  if (compact) {
    return <CompactQualityBadge metrics={metrics} />;
  }

  const {
    substance_score,
    completeness_score,
    depth_score,
    accuracy_score,
    overall_score,
    quality_gate_passed,
    query_complexity,
  } = metrics;

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              Quality Assessment
              {quality_gate_passed ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : (
                <AlertCircle className="h-5 w-5 text-yellow-600" />
              )}
            </CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              {quality_gate_passed
                ? "All quality standards met"
                : "Some areas may need review"}
            </p>
          </div>
          {query_complexity && (
            <Badge variant={getComplexityBadgeVariant(query_complexity)}>
              Level {query_complexity}: {getComplexityLabel(query_complexity)}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {showDetails && (
          <>
            <ScoreRow
              label="Substance"
              score={substance_score}
              description="Ratio of actual content vs metadata (80%+ required for passing)"
            />
            <ScoreRow
              label="Completeness"
              score={completeness_score}
              description="All sub-questions and requirements addressed"
            />
            <ScoreRow
              label="Depth"
              score={depth_score}
              description="Appropriate depth for query complexity level"
            />
            <ScoreRow
              label="Accuracy"
              score={accuracy_score}
              description="Correctness of claims, code, and mathematical statements"
            />

            <div className="pt-3 border-t dark:border-gray-700" />
          </>
        )}

        <ScoreRow
          label="Overall Quality"
          score={overall_score}
          description="Weighted average of all quality dimensions"
          className="font-bold"
        />

        <div className="pt-2 flex items-center justify-between text-xs text-gray-500">
          <span>
            Quality Gate:{" "}
            <span
              className={
                quality_gate_passed ? "text-green-600" : "text-yellow-600"
              }
            >
              {quality_gate_passed ? "✓ PASSED" : "⚠ REVIEW NEEDED"}
            </span>
          </span>
          {overall_score >= 9 && (
            <div className="flex items-center gap-1 text-green-600">
              <TrendingUp className="h-3 w-3" />
              <span className="font-medium">Exceptional</span>
            </div>
          )}
          {overall_score < 7 && (
            <div className="flex items-center gap-1 text-orange-600">
              <TrendingDown className="h-3 w-3" />
              <span className="font-medium">Can Improve</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default QualityScoreCard;
