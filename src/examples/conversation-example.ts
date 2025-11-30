/**
 * Example: Demonstrating conversation flow with entity resolution
 * 
 * This example shows how the system handles:
 * 1. Initial question about Donald Trump
 * 2. Follow-up question with pronoun "he"
 * 3. Entity resolution rewriting "When was he born?" → "When was Donald Trump born?"
 */

import { ContextManager } from "../context/ContextManager";
import { historyStore } from "../context/HistoryStore";
import { entityResolver } from "../context/EntityResolver";
import { llmRouter } from "../router/LlmRouter";

async function exampleConversation() {
  const sessionId = "example-session-123";
  const contextManager = new ContextManager(historyStore);

  console.log("=== Example Conversation Flow ===\n");

  // Turn 1: User asks about Donald Trump
  console.log("Turn 1:");
  const message1 = "Who is Donald Trump?";
  console.log(`User: "${message1}"`);

  contextManager.addUserMessage(sessionId, message1);

  // Get context and resolve (first message, no resolution needed)
  const recentMessages1 = contextManager.getRecentMessages(sessionId, 10);
  const resolution1 = await entityResolver.resolve(recentMessages1, message1);
  console.log(`Resolved: "${resolution1.resolvedQuery}"`);
  console.log(`Entities: ${JSON.stringify(resolution1.entities)}\n`);

  // Simulate assistant response (in real flow, this comes from LLM)
  const assistantResponse1 =
    "Donald Trump is a businessman and former President of the United States.";
  contextManager.addAssistantMessage(sessionId, assistantResponse1);
  console.log(`Assistant: "${assistantResponse1}"\n`);

  // Turn 2: User asks follow-up with pronoun
  console.log("Turn 2:");
  const message2 = "When was he born?";
  console.log(`User: "${message2}"`);

  contextManager.addUserMessage(sessionId, message2);

  // Get context and resolve (this should resolve "he" → "Donald Trump")
  const recentMessages2 = contextManager.getRecentMessages(sessionId, 10);
  const resolution2 = await entityResolver.resolve(recentMessages2, message2);
  console.log(`Resolved: "${resolution2.resolvedQuery}"`);
  console.log(`Entities: ${JSON.stringify(resolution2.entities)}\n`);

  // Show what would be sent to LLM
  const contextWindow = contextManager.getContextWindow(sessionId, 20);
  console.log("Context window sent to LLM:");
  console.log(JSON.stringify(contextWindow, null, 2));

  // In a real scenario, you would call:
  // const llmResponse = await llmRouter.routeChat({
  //   provider: "openai",
  //   systemPrompt: contextManager.getOrCreateSystemPrompt(),
  //   messages: [
  //     ...contextWindow.slice(0, -1),
  //     { role: "user", content: resolution2.resolvedQuery },
  //   ],
  // });
  // console.log(`Assistant: "${llmResponse.content}"`);

  console.log("\n=== Example Complete ===");
}

// Uncomment to run:
// exampleConversation().catch(console.error);








