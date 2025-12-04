export type StageId =
  | "analyst"
  | "researcher"
  | "creator"
  | "critic"
  | "reviews"
  | "director";

export type StageStatus = "idle" | "running" | "done" | "error";

export interface StageState {
  id: StageId;
  label: string;
  modelName?: string;
  status: StageStatus;
}

export const INITIAL_STAGES: StageState[] = [
  { id: "analyst", label: "Analyst", status: "idle" },
  { id: "researcher", label: "Researcher", status: "idle" },
  { id: "creator", label: "Creator", status: "idle" },
  { id: "critic", label: "Critic", status: "idle" },
  { id: "reviews", label: "LLM Council Review", status: "idle" },
  { id: "director", label: "Director", status: "idle" },
];
