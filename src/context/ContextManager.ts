/**
 * ContextManager: Single source of truth for conversation context
 * 
 * Manages context windows and system prompts for LLM interactions
 */

import { Message, MessageRole } from "../types";
import { HistoryStore } from "./HistoryStore";
import { DAC_SYSTEM_PROMPT } from "../config";

export class ContextManager {
  constructor(private historyStore: HistoryStore) {}

  /**
   * Add a user message to the conversation history
   */
  addUserMessage(sessionId: string, content: string, userId?: string): void {
    const message: Message = {
      role: "user",
      content,
      timestamp: Date.now(),
    };

    this.historyStore.appendMessage(sessionId, message, userId);
  }

  /**
   * Add an assistant message to the conversation history
   */
  addAssistantMessage(sessionId: string, content: string): void {
    const message: Message = {
      role: "assistant",
      content,
      timestamp: Date.now(),
    };

    this.historyStore.appendMessage(sessionId, message);
  }

  /**
   * Get context window (recent messages) to send to LLM
   * Returns messages formatted for LLM API
   */
  getContextWindow(
    sessionId: string,
    limit?: number
  ): Array<{ role: MessageRole; content: string }> {
    const messages = this.historyStore.getRecentMessages(
      sessionId,
      limit || 20
    );

    // Convert to LLM format (exclude timestamp)
    return messages.map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));
  }

  /**
   * Get the main DAC system prompt
   */
  getOrCreateSystemPrompt(): string {
    return DAC_SYSTEM_PROMPT;
  }

  /**
   * Get recent messages as Message objects (for EntityResolver)
   */
  getRecentMessages(sessionId: string, limit: number = 10): Message[] {
    return this.historyStore.getRecentMessages(sessionId, limit);
  }

  /**
   * TODO: History summarization for long conversations
   * 
   * Interface for future implementation:
   * - When conversation exceeds token limit, summarize older messages
   * - Keep recent messages verbatim
   * - Add summary as a system message or special message
   */
  // async summarizeHistory(sessionId: string): Promise<void> {
  //   // TODO: Implement summarization logic
  // }
}








