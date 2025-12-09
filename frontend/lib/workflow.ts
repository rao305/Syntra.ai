export type WorkflowRole = "analyst" | "researcher" | "creator" | "critic" | "reviews" | "director" | "synthesizer";
export type WorkflowModel = "gpt" | "gemini" | "perplexity" | "kimi" | "multi";
export type WorkflowMode = "manual" | "auto";
export type WorkflowStatus = "pending" | "running" | "awaiting_user" | "done" | "error" | "cancelled";

export type WorkflowStep = {
    id: string;
    role: WorkflowRole;
    model: WorkflowModel;
    mode: WorkflowMode;
    status: WorkflowStatus;
    inputContext: string;
    outputDraft?: string;
    outputFinal?: string;
    metadata?: {
        isMock?: boolean;
        providerName?: string;
        processing_time_ms?: number;
        latency_ms?: number;
    };
    error?: {
        message: string;
        provider?: string;
        type?: "config" | "network" | "rate_limit" | "timeout" | "unknown";
    };
};

export const DEFAULT_WORKFLOW: WorkflowStep[] = [
    { id: "analyst", role: "analyst", model: "gemini", mode: "auto", status: "pending", inputContext: "" },
    { id: "researcher", role: "researcher", model: "perplexity", mode: "auto", status: "pending", inputContext: "" },
    { id: "creator", role: "creator", model: "gpt", mode: "auto", status: "pending", inputContext: "" },
    { id: "critic", role: "critic", model: "kimi", mode: "auto", status: "pending", inputContext: "" },
    { id: "reviews", role: "reviews", model: "multi", mode: "auto", status: "pending", inputContext: "" },
    { id: "director", role: "director", model: "gpt", mode: "auto", status: "pending", inputContext: "" },
];
