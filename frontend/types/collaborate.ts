import { z } from "zod";

// ===== Core Models =====

export const ModelInfoSchema = z.object({
  provider: z.enum(["openai", "google", "perplexity", "kimi", "openrouter"]),
  model_slug: z.string(),
  display_name: z.string(),
});

export type ModelInfo = z.infer<typeof ModelInfoSchema>;

// ===== Inner Pipeline Types =====

export const InternalStageRoleSchema = z.enum([
  "analyst",
  "researcher",
  "creator",
  "critic",
  "internal_synth",
]);

export type InternalStageRole = z.infer<typeof InternalStageRoleSchema>;

export const TokenUsageSchema = z.object({
  input_tokens: z.number(),
  output_tokens: z.number(),
});

export type TokenUsage = z.infer<typeof TokenUsageSchema>;

export const InternalStageSchema = z.object({
  id: z.string(),
  role: InternalStageRoleSchema,
  title: z.string(),
  model: ModelInfoSchema,
  content: z.string(),
  created_at: z.string().datetime(),
  token_usage: TokenUsageSchema.optional(),
  latency_ms: z.number().optional(),
  used_in_final_answer: z.boolean().optional(),
});

export type InternalStage = z.infer<typeof InternalStageSchema>;

export const CompressedReportSchema = z.object({
  model: ModelInfoSchema,
  content: z.string(),
});

export type CompressedReport = z.infer<typeof CompressedReportSchema>;

export const InternalPipelineSchema = z.object({
  stages: z.array(InternalStageSchema),
  compressed_report: CompressedReportSchema.optional(),
});

export type InternalPipeline = z.infer<typeof InternalPipelineSchema>;

// ===== External Council Review Types =====

export const ReviewStanceSchema = z.enum([
  "agree",
  "disagree",
  "mixed",
  "unknown",
]);

export type ReviewStance = z.infer<typeof ReviewStanceSchema>;

export const ExternalReviewerSourceSchema = z.enum([
  "perplexity",
  "gemini",
  "gpt",
  "kimi",
  "openrouter",
]);

export type ExternalReviewerSource = z.infer<typeof ExternalReviewerSourceSchema>;

export const ExternalReviewSchema = z.object({
  id: z.string(),
  source: ExternalReviewerSourceSchema,
  model: ModelInfoSchema,
  stance: ReviewStanceSchema,
  content: z.string(),
  created_at: z.string().datetime(),
  token_usage: TokenUsageSchema.optional(),
  latency_ms: z.number().optional(),
});

export type ExternalReview = z.infer<typeof ExternalReviewSchema>;

// ===== Final Answer Types =====

export const ConfidenceLevelSchema = z.enum(["low", "medium", "high"]);

export type ConfidenceLevel = z.infer<typeof ConfidenceLevelSchema>;

export const FinalAnswerExplanationSchema = z.object({
  used_internal_report: z.boolean(),
  external_reviews_considered: z.number(),
  confidence_level: ConfidenceLevelSchema,
});

export type FinalAnswerExplanation = z.infer<typeof FinalAnswerExplanationSchema>;

export const FinalAnswerSchema = z.object({
  content: z.string(),
  model: ModelInfoSchema,
  created_at: z.string().datetime(),
  explanation: FinalAnswerExplanationSchema.optional(),
});

export type FinalAnswer = z.infer<typeof FinalAnswerSchema>;

// ===== Metadata Types =====

export const CollaborateRunMetaSchema = z.object({
  run_id: z.string(),
  mode: z.enum(["auto", "manual"]),
  started_at: z.string().datetime(),
  finished_at: z.string().datetime(),
  total_latency_ms: z.number().optional(),
  models_involved: z.array(ModelInfoSchema),
});

export type CollaborateRunMeta = z.infer<typeof CollaborateRunMetaSchema>;

// ===== Main Response Type =====

export const CollaborateResponseSchema = z.object({
  final_answer: FinalAnswerSchema,
  internal_pipeline: InternalPipelineSchema,
  external_reviews: z.array(ExternalReviewSchema),
  meta: CollaborateRunMetaSchema,
});

export type CollaborateResponse = z.infer<typeof CollaborateResponseSchema>;

// ===== Request Types =====

export const CollaborateRequestSchema = z.object({
  message: z.string().min(1, "Message cannot be empty"),
  mode: z.enum(["auto", "manual"]).default("auto"),
});

export type CollaborateRequest = z.infer<typeof CollaborateRequestSchema>;

// ===== Helper Functions =====

/**
 * Parse and validate a collaboration response from the API
 */
export function parseCollaborateResponse(data: unknown): CollaborateResponse {
  return CollaborateResponseSchema.parse(data);
}

/**
 * Get total token usage across all stages
 */
export function getTotalTokenUsage(response: CollaborateResponse): {
  input: number;
  output: number;
  total: number;
} {
  let inputTokens = 0;
  let outputTokens = 0;

  // Count tokens from inner pipeline stages
  for (const stage of response.internal_pipeline.stages) {
    if (stage.token_usage) {
      inputTokens += stage.token_usage.input_tokens;
      outputTokens += stage.token_usage.output_tokens;
    }
  }

  // Count tokens from compressed report
  if (response.internal_pipeline.compressed_report?.model) {
    // This would need to be added to the response if tracking is needed
  }

  // Count tokens from external reviews
  for (const review of response.external_reviews) {
    if (review.token_usage) {
      inputTokens += review.token_usage.input_tokens;
      outputTokens += review.token_usage.output_tokens;
    }
  }

  return {
    input: inputTokens,
    output: outputTokens,
    total: inputTokens + outputTokens,
  };
}

/**
 * Format latency in human-readable form
 */
export function formatLatency(ms: number | undefined): string {
  if (!ms) return "N/A";
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Get average latency per stage
 */
export function getAverageLatency(response: CollaborateResponse): number {
  const stages = response.internal_pipeline.stages;
  if (!stages.length) return 0;

  const totalLatency = stages.reduce((sum, stage) => sum + (stage.latency_ms || 0), 0);
  return totalLatency / stages.length;
}

/**
 * Check if collaboration was successful
 */
export function isSuccessful(response: CollaborateResponse): boolean {
  return (
    !!response.final_answer?.content &&
    response.internal_pipeline.stages.length > 0 &&
    response.meta?.finished_at
  );
}

/**
 * Get confidence badge color
 */
export function getConfidenceColor(
  level: ConfidenceLevel
): "green" | "yellow" | "red" {
  switch (level) {
    case "high":
      return "green";
    case "medium":
      return "yellow";
    case "low":
      return "red";
  }
}

/**
 * Get stance badge color
 */
export function getStanceColor(
  stance: ReviewStance
): "green" | "yellow" | "red" | "gray" {
  switch (stance) {
    case "agree":
      return "green";
    case "disagree":
      return "red";
    case "mixed":
      return "yellow";
    case "unknown":
      return "gray";
  }
}
