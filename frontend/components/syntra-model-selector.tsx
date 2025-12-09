import { Brain, Code2, Search, Sparkles } from "lucide-react";

export const SYNTRA_MODELS = [
  {
    id: 'auto',
    name: 'Auto',
    provider: 'auto',
    icon: Sparkles,
    description: 'Automatically select the best model for your task'
  },
  {
    id: 'gpt',
    name: 'GPT-4',
    provider: 'openai',
    icon: Brain,
    description: 'OpenAI GPT-4 for general purpose tasks'
  },
  {
    id: 'gemini',
    name: 'Gemini',
    provider: 'google',
    icon: Code2,
    description: 'Google Gemini for multimodal and research tasks'
  },
  {
    id: 'perplexity',
    name: 'Perplexity',
    provider: 'perplexity',
    icon: Search,
    description: 'Perplexity for web search and research'
  },
];

export function SyntraModelSelector() {
  return null;
}
