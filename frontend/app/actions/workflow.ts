"use server"

import dotenv from "dotenv"
import fs from "fs"
import path from "path"

import {
    callGemini,
    callGPT,
    callKimi,
    callPerplexity,
    ModelResponse
} from "@/lib/models"
import {
    IS_MOCK_MODE,
    isGeminiAvailable,
    isGptAvailable,
    isKimiAvailable,
    isPerplexityAvailable
} from "@/lib/providersConfig"
import { DEFAULT_WORKFLOW, WorkflowModel, WorkflowRole, WorkflowStep } from "@/lib/workflow"

// Load backend .env so we can reuse provider keys without duplicating them in the frontend env
function loadBackendEnv() {
    if (typeof process !== "undefined" && process.env.BACKEND_ENV_LOADED !== "1") {
        try {
            const cwd = process.cwd()
            console.log(`[workflow] Current working directory: ${cwd}`)

            // Try multiple possible paths for the backend .env
            const possiblePaths = [
                path.resolve(cwd, "../backend/.env"),
                path.resolve(cwd, "backend/.env"),
                path.resolve(cwd, "..", "backend", ".env"),
                path.join(cwd, "..", "backend", ".env"),
                // Also try from __dirname if available
                path.resolve(__dirname, "../../backend/.env"),
                path.resolve(__dirname, "../../../backend/.env"),
            ]

            console.log(`[workflow] Trying paths:`, possiblePaths)

            for (const backendEnvPath of possiblePaths) {
                console.log(`[workflow] Checking: ${backendEnvPath}, exists: ${fs.existsSync(backendEnvPath)}`)
                if (fs.existsSync(backendEnvPath)) {
                    const result = dotenv.config({ path: backendEnvPath })
                    if (result.error) {
                        console.error(`[workflow] Error loading ${backendEnvPath}:`, result.error)
                        continue
                    }
                    process.env.BACKEND_ENV_LOADED = "1"
                    console.log(`[workflow] ✅ Loaded backend environment variables from ${backendEnvPath}`)
                    console.log(`[workflow] KIMI_API_KEY present: ${!!process.env.KIMI_API_KEY}`)
                    console.log(`[workflow] OPENAI_API_KEY present: ${!!process.env.OPENAI_API_KEY}`)
                    console.log(`[workflow] GEMINI_API_KEY present: ${!!process.env.GEMINI_API_KEY}`)
                    console.log(`[workflow] PERPLEXITY_API_KEY present: ${!!process.env.PERPLEXITY_API_KEY}`)
                    return true
                }
            }

            console.warn(`[workflow] ❌ Backend .env not found in any of the tried paths`)
        } catch (error) {
            console.error("[workflow] Failed to load backend .env:", error)
        }
    } else if (process.env.BACKEND_ENV_LOADED === "1") {
        console.log(`[workflow] Backend env already loaded`)
    }
    return false
}

// Load env immediately
loadBackendEnv()

// Check provider availability dynamically (not at module load time)
function getProviderAvailability(): Record<WorkflowModel, boolean> {
    // Ensure env is loaded
    loadBackendEnv()

    return {
        gpt: isGptAvailable() || IS_MOCK_MODE,
        gemini: isGeminiAvailable() || IS_MOCK_MODE,
        perplexity: isPerplexityAvailable() || IS_MOCK_MODE,
        kimi: isKimiAvailable() || IS_MOCK_MODE,
        multi: true
    }
}

// Get the first available fallback model (called dynamically)
function getAvailableFallbackModel(): WorkflowModel {
    const availability = getProviderAvailability()
    return (Object.keys(availability) as WorkflowModel[]).find((model) => availability[model]) || "gpt"
}

// Check if a specific model is available (called dynamically)
function isModelAvailable(model: WorkflowModel): boolean {
    const availability = getProviderAvailability()
    console.log(`[workflow] Checking if ${model} is available:`, availability[model])
    return availability[model] === true
}

// System prompts for each role
const PROMPTS = {
    analyst: `You are an expert Analyst in a collaborative AI team. Your goal is to deeply understand the user's request.
    
    Output Requirements:
    1.  **Deconstruct the Request**: Break down the user's query into core components and implicit needs.
    2.  **Identify Constraints**: List any technical, logical, or creative constraints.
    3.  **Edge Cases**: Anticipate potential pitfalls or edge cases.
    4.  **Strategic Direction**: Propose a high-level strategy for the team to follow.
    
    Format your response as a structured markdown report. Be comprehensive.`,

    researcher: `You are an expert Researcher in a collaborative AI team. Your goal is to gather factual information to support the Analyst's strategy.
    
    Output Requirements:
    1.  **Targeted Search**: Based on the Analyst's breakdown, simulate a search for the most relevant, up-to-date information.
    2.  **Key Findings**: Summarize the top 3-5 key facts, libraries, or concepts found.
    3.  **Technical Details**: Provide specific version numbers, API details, or syntax examples if relevant.
    4.  **Sources**: List simulated URLs for the information.
    
    Do not answer the final user question directly. Focus purely on providing raw, high-quality data for the Creator.`,

    creator: `You are an expert Creator in a collaborative AI team. Your goal is to synthesize the Analyst's strategy and the Researcher's data into a concrete solution.
    
    Output Requirements:
    1.  **Solution Design**: Create a detailed plan or architecture based on the analysis and research.
    2.  **Implementation**: Write the actual code, draft, or content. Use clean, commented, and professional syntax.
    3.  **Explanation**: Explain *why* you made specific choices, referencing the research findings.
    
    Be bold and creative. Produce a high-quality draft that is ready for critique.`,

    critic: `You are an expert Critic in a collaborative AI team. Your goal is to refine the Creator's work.
    
    Output Requirements:
    1.  **Logic Check**: Identify any logical fallacies or bugs in the Creator's solution.
    2.  **Safety & Security**: Check for vulnerabilities or unsafe practices.
    3.  **Optimization**: Suggest specific improvements for performance or readability.
    4.  **Constructive Feedback**: Be tough but fair. If the solution is great, validate it but suggest one "stretch" improvement.`,

    synthesizer: `You are an expert Synthesizer in a collaborative AI team. Your goal is to deliver the final answer to the user.
    
    Output Requirements:
    1.  **Executive Summary**: A concise answer to the user's original request.
    2.  **Final Solution**: Present the polished code, content, or plan, incorporating the Creator's work and the Critic's improvements.
    3.  **Rationale**: Briefly explain how the team arrived at this solution.
    4.  **Next Steps**: Suggest actionable next steps for the user.
    
    Your output should be the definitive, high-quality response the user sees.`
}

/**
 * Intelligently assigns models to workflow steps based on:
 * - Step role requirements
 * - Query characteristics
 * - Model strengths
 * - Ensures all models are used (diversity)
 */
function assignModelsIntelligently(userMessage: string): WorkflowModel[] {
    const availableModels: WorkflowModel[] = ["gpt", "gemini", "perplexity", "kimi"]
    const query = userMessage.toLowerCase()

    // Model strengths mapping
    const modelStrengths = {
        analyst: {
            // Analyst needs: reasoning, analysis, deconstruction
            gpt: 0.9,      // Strong reasoning
            gemini: 0.8,   // Good analysis
            kimi: 0.7,     // Long context for complex analysis
            perplexity: 0.5 // Less ideal for pure analysis
        },
        researcher: {
            // Researcher needs: web search, real-time info, citations
            perplexity: 1.0, // Best for web search
            gemini: 0.6,     // Can do some research
            gpt: 0.5,        // Limited web search
            kimi: 0.4        // Not ideal for research
        },
        creator: {
            // Creator needs: code generation, creative writing, synthesis
            gpt: 0.9,      // Excellent for code
            gemini: 0.85,  // Great for code and creative
            kimi: 0.8,    // Long context for long-form content
            perplexity: 0.4 // Not ideal for creation
        },
        critic: {
            // Critic needs: logical analysis, error detection, refinement
            gpt: 0.95,     // Best for critical analysis
            gemini: 0.8,   // Good reasoning
            kimi: 0.7,     // Can analyze long content
            perplexity: 0.5 // Less ideal
        },
        synthesizer: {
            // Synthesizer needs: summarization, integration, final output
            gemini: 0.9,   // Excellent summarization
            gpt: 0.85,     // Good synthesis
            kimi: 0.8,     // Can handle long context
            perplexity: 0.6 // Can synthesize research
        }
    }

    // Query-based adjustments
    const queryFeatures = {
        hasCode: /code|script|function|program|algorithm|python|javascript|java|c\+\+|sql/i.test(query),
        hasMath: /calculate|equation|formula|solve|compute|math|statistics/i.test(query),
        hasResearch: /research|find|search|latest|current|news|recent|what is|how does/i.test(query),
        hasCreative: /write|create|story|poem|essay|article|blog|content/i.test(query),
        isComplex: query.length > 200 || /analyze|explain|compare|evaluate|discuss/i.test(query)
    }

    // Adjust scores based on query features
    if (queryFeatures.hasCode) {
        modelStrengths.creator.gpt += 0.1
        modelStrengths.creator.gemini += 0.1
    }
    if (queryFeatures.hasMath) {
        modelStrengths.analyst.gpt += 0.1
        modelStrengths.critic.gpt += 0.1
    }
    if (queryFeatures.hasResearch) {
        modelStrengths.researcher.perplexity += 0.2
    }
    if (queryFeatures.hasCreative) {
        modelStrengths.creator.kimi += 0.1
        modelStrengths.creator.gemini += 0.1
    }
    if (queryFeatures.isComplex) {
        modelStrengths.analyst.kimi += 0.1
        modelStrengths.synthesizer.kimi += 0.1
    }

    // Assign models to steps
    const roles: WorkflowRole[] = ["analyst", "researcher", "creator", "critic", "synthesizer"]
    const assignments: WorkflowModel[] = []
    const usedModels = new Set<WorkflowModel>()

    // First pass: assign best model for each role
    for (const role of roles) {
        const scores = modelStrengths[role]
        const sortedModels = Object.entries(scores)
            .sort((a, b) => b[1] - a[1])
            .map(([model]) => model as WorkflowModel)

        // Filter to models that actually have API keys (unless mock)
        const availableSorted = sortedModels.filter((model) => isModelAvailable(model))
        const candidates = availableSorted.length > 0 ? availableSorted : sortedModels

        // Find best available model (prioritize unused models for diversity)
        let assignedModel: WorkflowModel | null = null
        for (const model of candidates) {
            if (isModelAvailable(model) && !usedModels.has(model)) {
                assignedModel = model
                break
            }
        }

        // If no unused available model, pick first available candidate
        if (!assignedModel) {
            assignedModel = candidates.find((model) => isModelAvailable(model)) || getAvailableFallbackModel()
        }

        assignments.push(assignedModel)
        if (isModelAvailable(assignedModel)) {
            usedModels.add(assignedModel)
        }
    }

    // Ensure all models are used at least once (diversity requirement)
    const unusedModels = availableModels.filter(m => !usedModels.has(m) && isModelAvailable(m))
    if (unusedModels.length > 0) {
        // Replace assignments to ensure all models are used
        // Find steps where unused models are acceptable
        for (let i = 0; i < unusedModels.length; i++) {
            const unusedModel = unusedModels[i]

            // Find the best step to assign this unused model
            let bestStepIndex = -1
            let bestScore = 0

            for (let j = 0; j < roles.length; j++) {
                const role = roles[j]
                const scores = modelStrengths[role]
                const currentScore = scores[unusedModel]

                // Prefer steps where this model has a good score and current assignment can be moved
                if (currentScore >= 0.4 && currentScore > bestScore && isModelAvailable(unusedModel)) {
                    // Check if we can swap this assignment
                    const currentModel = assignments[j]
                    const canSwap = scores[currentModel] >= 0.4 // Current model is also acceptable

                    if (canSwap) {
                        bestStepIndex = j
                        bestScore = currentScore
                    }
                }
            }

            // Assign the unused model to the best step found
            if (bestStepIndex >= 0) {
                assignments[bestStepIndex] = unusedModel
                usedModels.add(unusedModel)
            }
        }
    }

    // Add anonymity: randomly shuffle assignments if models have similar scores
    // This prevents pattern detection while maintaining quality
    for (let i = 0; i < assignments.length - 1; i++) {
        const currentRole = roles[i]
        const nextRole = roles[i + 1]
        const currentScores = modelStrengths[currentRole]
        const nextScores = modelStrengths[nextRole]

        const currentModel = assignments[i]
        const nextModel = assignments[i + 1]

        // Calculate how well each model fits both roles
        const currentModelFit = (currentScores[currentModel] + nextScores[currentModel]) / 2
        const nextModelFit = (currentScores[nextModel] + nextScores[nextModel]) / 2

        // If both models fit similarly well (within 15%), randomly swap for anonymity
        const fitDiff = Math.abs(currentModelFit - nextModelFit)
        const avgFit = (currentModelFit + nextModelFit) / 2

        if (fitDiff / avgFit < 0.15 && Math.random() > 0.6) {
            [assignments[i], assignments[i + 1]] = [assignments[i + 1], assignments[i]]
        }
    }

    // Final check: ensure at least 3 different models are used (for 5 steps with 4 models)
    const uniqueModels = new Set(assignments)
    if (uniqueModels.size < 3) {
        // Force more diversity by replacing duplicates
        const modelCounts = new Map<WorkflowModel, number>()
        assignments.forEach(m => modelCounts.set(m, (modelCounts.get(m) || 0) + 1))

        // Find models used more than once
        const duplicates = Array.from(modelCounts.entries())
            .filter(([_, count]) => count > 1)
            .sort((a, b) => b[1] - a[1])

        // Replace duplicates with less-used models
        for (const [duplicateModel, count] of duplicates) {
            if (count > 1) {
                const availableReplacements = availableModels.filter(m =>
                    modelCounts.get(m)! < 2 && m !== duplicateModel
                )

                if (availableReplacements.length > 0) {
                    // Find a step using duplicate that can use replacement
                    for (let i = 0; i < assignments.length; i++) {
                        if (assignments[i] === duplicateModel) {
                            const role = roles[i]
                            const scores = modelStrengths[role]

                            // Find best replacement
                            const bestReplacement = availableReplacements
                                .map(m => ({ model: m, score: scores[m] }))
                                .sort((a, b) => b.score - a.score)[0]

                            if (bestReplacement && bestReplacement.score >= 0.4 && isModelAvailable(bestReplacement.model)) {
                                assignments[i] = bestReplacement.model
                                modelCounts.set(duplicateModel, modelCounts.get(duplicateModel)! - 1)
                                modelCounts.set(bestReplacement.model, (modelCounts.get(bestReplacement.model) || 0) + 1)
                                break
                            }
                        }
                    }
                }
            }
        }
    }

    return assignments
}

export async function startWorkflow(userMessage: string) {
    const steps = JSON.parse(JSON.stringify(DEFAULT_WORKFLOW)) as WorkflowStep[]

    // Intelligently assign models based on query and step requirements
    const modelAssignments = assignModelsIntelligently(userMessage)

    // Apply model assignments
    steps.forEach((step, index) => {
        step.model = modelAssignments[index]
        step.status = "pending"
        if (index === 0) {
            step.inputContext = userMessage
        }
    })

    // Log intelligent assignments (for transparency, but assignments are dynamic)
    const assignmentSummary = steps.map(s => `${s.role}:${s.model}`).join(', ')
    const uniqueModels = new Set(modelAssignments)
    console.log(`🎯 Intelligent model assignment (${uniqueModels.size} unique models):`, assignmentSummary)
    console.log(`📊 Model distribution:`, Array.from(uniqueModels).map(m => {
        const count = modelAssignments.filter(ma => ma === m).length
        return `${m}:${count}x`
    }).join(', '))

    return steps
}

// Define the return type explicitly to ensure proper serialization
type StepResult = {
    outputDraft: string
    status: "done" | "awaiting_user" | "error"
    errorMessage?: string
    errorProvider?: string
    errorType?: string
    metadata: {
        isMock: boolean
        providerName: WorkflowModel
    }
}

export async function runStep(stepId: string, inputContext: string, previousSteps: WorkflowStep[] = []): Promise<StepResult> {
    const step = previousSteps.find(s => s.id === stepId)
    if (!step) {
        console.error(`❌ Step ${stepId} not found in previousSteps`)
        // Return error result instead of throwing
        return {
            outputDraft: "",
            status: "error",
            errorMessage: `Step ${stepId} not found`,
            errorProvider: "system",
            errorType: "config",
            metadata: {
                isMock: false,
                providerName: "gpt"
            }
        }
    }

    const role = step.role
    const model = step.model
    const systemPrompt = PROMPTS[role]

    console.log(`🚀 [runStep] Starting step ${stepId} (${role}) with model ${model}`)
    console.log(`📊 [runStep] Model availability:`, {
        gpt: isGptAvailable(),
        gemini: isGeminiAvailable(),
        perplexity: isPerplexityAvailable(),
        kimi: isKimiAvailable(),
        mockMode: IS_MOCK_MODE,
        selectedModel: model,
        selectedModelAvailable: isModelAvailable(model)
    })

    // Construct context from previous steps
    let fullContext = `User Request: ${inputContext}\n\n`

    previousSteps.forEach(s => {
        if ((s.status === "done" || s.status === "awaiting_user") && s.outputFinal) {
            fullContext += `\n\n--- [${s.role.toUpperCase()}] Output ---\n${s.outputFinal}\n`
        }
    })

    console.log(`📝 [runStep] Context length: ${fullContext.length} characters`)

    let result = ""
    let isMock = false
    let errorDetails: WorkflowStep['error'] = undefined

    try {
        const timeoutPromise = new Promise<ModelResponse>((_, reject) => {
            setTimeout(() => reject(new Error("Step execution timed out")), 120000); // 120s timeout (increased for synthesizer with large context)
        });

        let responsePromise: Promise<ModelResponse> | undefined;

        if (model === "gpt") {
            responsePromise = callGPT([
                { role: "system", content: systemPrompt },
                { role: "user", content: fullContext }
            ])
        } else if (model === "gemini") {
            responsePromise = callGemini(`${systemPrompt}\n\n${fullContext}`)
        } else if (model === "perplexity") {
            responsePromise = callPerplexity([
                { role: "system", content: systemPrompt },
                { role: "user", content: fullContext }
            ])
        } else if (model === "kimi") {
            responsePromise = callKimi([
                { role: "system", content: systemPrompt },
                { role: "user", content: fullContext }
            ])
        }

        if (responsePromise) {
            console.log(`⏳ [runStep] Waiting for ${model} response (timeout: 70s)...`)

            try {
                const response = await Promise.race([responsePromise, timeoutPromise]);

                if (response) {
                    console.log(`✅ [runStep] Received response from ${model}, content length: ${response.content?.length || 0}`)
                    result = response.content || ""
                    isMock = !!response.isMock

                    // Check if the response contains an error
                    if (response.error) {
                        console.error(`❌ Model ${model} returned error:`, response.error);
                        // Determine error type based on error message
                        const errorMsg = String(response.error).toLowerCase();
                        let errorType: "config" | "network" | "rate_limit" | "timeout" | "unknown" = "unknown";

                        // Check for authentication/config errors first
                        if (errorMsg.includes('authentication') ||
                            errorMsg.includes('invalid_authentication') ||
                            (errorMsg.includes('invalid') && (errorMsg.includes('key') || errorMsg.includes('token') || errorMsg.includes('auth'))) ||
                            errorMsg.includes('api key') ||
                            errorMsg.includes('unauthorized') ||
                            errorMsg.includes('forbidden')) {
                            errorType = "config";
                        } else if (errorMsg.includes('rate limit') || errorMsg.includes('429') || errorMsg.includes('too many requests')) {
                            errorType = "rate_limit";
                        } else if (errorMsg.includes('timeout') || errorMsg.includes('timed out') || errorMsg.includes('exceeded')) {
                            errorType = "timeout";
                        } else if (errorMsg.includes('network') || errorMsg.includes('connection') || errorMsg.includes('fetch')) {
                            errorType = "network";
                        }

                        errorDetails = {
                            message: response.error,
                            provider: model,
                            type: errorType
                        }
                    }

                    // Check if content is empty and no error was set
                    if (!result && !errorDetails) {
                        console.error(`❌ Model ${model} returned empty content with no error`);
                        errorDetails = {
                            message: `${model} returned an empty response`,
                            provider: model,
                            type: "unknown"
                        }
                    }
                } else {
                    // No response at all
                    console.error(`❌ No response received from ${model}`);
                    errorDetails = {
                        message: `No response received from ${model}`,
                        provider: model,
                        type: "network"
                    }
                }
            } catch (raceError: any) {
                // Handle timeout or other race errors
                console.error(`❌ [runStep] Promise race error for ${model}:`, raceError);
                const errorMessage = raceError?.message || `Error calling ${model}`
                if (errorMessage.includes("timeout") || errorMessage.includes("timed out") || errorMessage.includes("exceeded")) {
                    errorDetails = {
                        message: `Request to ${model} timed out`,
                        provider: model,
                        type: "timeout"
                    }
                } else {
                    errorDetails = {
                        message: errorMessage,
                        provider: model,
                        type: "network"
                    }
                }
                // Don't re-throw - we've captured the error in errorDetails
                console.log(`📝 Captured race error in errorDetails:`, errorDetails);
            }
        } else {
            // No responsePromise (invalid model)
            console.error(`❌ Invalid model: ${model}`);
            errorDetails = {
                message: `Invalid or unsupported model: ${model}`,
                provider: model,
                type: "config"
            }
        }
    } catch (e: any) {
        console.error(`❌ Step ${stepId} failed:`, e)

        // Better error message extraction
        let errorMessage = "Unknown error";
        let errorType: "config" | "network" | "rate_limit" | "timeout" | "unknown" = "unknown";

        if (e instanceof Error) {
            errorMessage = e.message;

            // Check error name for type
            if (e.name === "ProviderConfigError") {
                errorType = "config";
            } else if (e.name === "ProviderCallError") {
                // ProviderCallError could be different types - check the message
                const msgLower = e.message.toLowerCase();
                if (msgLower.includes('authentication') || msgLower.includes('invalid') && msgLower.includes('key') || msgLower.includes('api key')) {
                    errorType = "config";
                } else if (msgLower.includes('rate limit') || msgLower.includes('429')) {
                    errorType = "rate_limit";
                } else if (msgLower.includes('timeout') || msgLower.includes('timed out')) {
                    errorType = "timeout";
                } else {
                    errorType = "network";
                }
            } else if (e.message?.includes("timeout") || e.message?.includes("timed out")) {
                errorType = "timeout";
            } else if (e.message?.includes("authentication") || (e.message?.includes("invalid") && e.message?.includes("key"))) {
                errorType = "config";
            }
        } else if (typeof e === 'string') {
            errorMessage = e;
        } else if (e && typeof e.toString === 'function') {
            errorMessage = e.toString();
        }

        // Check for rate limit
        if (e?.statusCode === 429 || errorMessage.includes("429") || errorMessage.includes("rate limit")) {
            errorType = "rate_limit";
        }

        // Log full error details for debugging
        console.error(`📋 Full error details for step ${stepId}:`, {
            message: errorMessage,
            type: errorType,
            name: e?.name,
            stack: e?.stack,
            provider: model
        });

        // Ensure error object is fully serializable (no Error instances)
        errorDetails = {
            message: errorMessage || `Failed to execute ${role} step with ${model}`,
            provider: model,
            type: errorType
        }
    }

    if (errorDetails) {
        // Ensure all error properties are plain strings (serializable)
        const errorMessage = String(errorDetails.message || `Failed to execute ${role} step with ${model}`)
        const errorProvider = String(errorDetails.provider || model)
        const errorType = String(errorDetails.type || "unknown")

        console.error(`❌ Step ${stepId} (${role}) returning error:`, {
            message: errorMessage,
            type: errorType,
            provider: errorProvider
        })

        // Return a plain object with only serializable properties
        const errorResult: StepResult = {
            outputDraft: "",
            status: "error",
            errorMessage: errorMessage,
            errorProvider: errorProvider,
            errorType: errorType,
            metadata: {
                isMock,
                providerName: model
            }
        }
        console.log(`📤 Returning error result:`, JSON.stringify(errorResult))
        return errorResult
    }

    const successResult: StepResult = {
        outputDraft: result,
        status: step.mode === "auto" ? "done" : "awaiting_user",
        metadata: {
            isMock,
            providerName: model
        }
    }
    console.log(`📤 Returning success result for ${stepId}, status: ${successResult.status}, output length: ${result.length}`)
    return successResult
}
