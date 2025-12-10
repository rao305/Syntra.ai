'use client'

import * as React from 'react'
import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import {
  ArrowRight,
  Headphones,
  Database,
  Code,
  Image as ImageIcon,
  TrendingUp,
  Settings,
  Brain,
  Code2,
  Sparkles,
} from 'lucide-react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import Reveal from '@/components/motion/Reveal'
import { MetricsStrip } from '@/components/metrics-strip'
import { UseCasesHero } from '@/components/use-cases-hero'
import { UseCaseDemo } from '@/components/use-case-demo'

// Model definitions
const models = {
  claude: {
    id: 'claude',
    name: 'Claude',
    tag: 'Reasoning',
    icon: Brain,
    color: 'bg-gradient-to-r from-orange-500/20 to-orange-600/20 border-orange-500/40 text-orange-400',
    iconColor: 'text-orange-400',
  },
  openai: {
    id: 'openai',
    name: 'OpenAI',
    tag: 'Code',
    icon: Code2,
    color: 'bg-gradient-to-r from-green-500/20 to-green-600/20 border-green-500/40 text-green-400',
    iconColor: 'text-green-400',
  },
  gemini: {
    id: 'gemini',
    name: 'Gemini',
    tag: 'Image',
    icon: ImageIcon,
    color: 'bg-gradient-to-r from-blue-500/20 to-blue-600/20 border-blue-500/40 text-blue-400',
    iconColor: 'text-blue-400',
  },
  local: {
    id: 'local',
    name: 'Local RAG',
    tag: 'Retrieval',
    icon: Database,
    color: 'bg-gradient-to-r from-purple-500/20 to-purple-600/20 border-purple-500/40 text-purple-400',
    iconColor: 'text-purple-400',
  },
  ensemble: {
    id: 'ensemble',
    name: 'Syntra Ensemble',
    tag: 'Multi-Model',
    icon: Sparkles,
    color: 'bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border-emerald-500/40 text-emerald-400',
    iconColor: 'text-emerald-400',
  },
}

// Use Case Demo Data
const useCaseDemos = {
  support: {
    models: [models.claude, models.local, models.openai],
    steps: [
      {
        step: 1,
        activeModel: 'claude',
        messages: [
          {
            id: 1,
            role: 'user',
            content: "I'm having trouble with my account login. It says 'invalid credentials' but I'm sure my password is correct.",
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I understand you're experiencing login issues. Let me analyze this problem and find relevant solutions from our knowledge base.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
        ],
        routingNote: 'Task: Complex reasoning → Model: Claude',
      },
      {
        step: 2,
        activeModel: 'local',
        messages: [
          {
            id: 1,
            role: 'user',
            content: "I'm having trouble with my account login. It says 'invalid credentials' but I'm sure my password is correct.",
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I understand you're experiencing login issues. Let me analyze this problem and find relevant solutions from our knowledge base.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              'Found 3 relevant KB articles:\n\n• "Password Reset Guide" (Article #1423)\n• "Two-Factor Authentication Setup" (Article #1891)\n• "Account Lockout Troubleshooting" (Article #2034)',
            model: 'Local RAG',
            modelTag: 'Retrieval',
          },
        ],
        routingNote: 'Task: Knowledge retrieval → Model: Local RAG',
      },
      {
        step: 3,
        activeModel: 'openai',
        messages: [
          {
            id: 1,
            role: 'user',
            content: "I'm having trouble with my account login. It says 'invalid credentials' but I'm sure my password is correct.",
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I understand you're experiencing login issues. Let me analyze this problem and find relevant solutions from our knowledge base.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              'Found 3 relevant KB articles:\n\n• "Password Reset Guide" (Article #1423)\n• "Two-Factor Authentication Setup" (Article #1891)\n• "Account Lockout Troubleshooting" (Article #2034)',
            model: 'Local RAG',
            modelTag: 'Retrieval',
          },
          {
            id: 4,
            role: 'assistant',
            content:
              "Based on the knowledge base, here's a personalized response:\n\nHi! I've found some solutions for your login issue. The most common cause is an account lockout after multiple failed attempts. Please try:\n\n1. Use the password reset link (I can send it to your email)\n2. Check if 2FA is enabled and verify your device\n3. Wait 15 minutes if your account is temporarily locked\n\nWould you like me to send a password reset link?",
            model: 'OpenAI',
            modelTag: 'Code',
          },
        ],
        routingNote: 'Task: Response generation → Model: OpenAI',
      },
    ],
  },
  knowledge: {
    models: [models.claude, models.local, models.openai],
    steps: [
      {
        step: 1,
        activeModel: 'claude',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'What is our company policy on remote work?',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll search our internal documentation for the remote work policy. Let me query our knowledge base.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
        ],
        routingNote: 'Task: Query understanding → Model: Claude',
      },
      {
        step: 2,
        activeModel: 'local',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'What is our company policy on remote work?',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll search our internal documentation for the remote work policy. Let me query our knowledge base.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              'Retrieved from HR Handbook v3.2:\n\n**Remote Work Policy**\n\n• Employees can work remotely up to 3 days per week\n• Requires manager approval\n• Must be available during core hours (10am-3pm EST)\n• Quarterly in-person meetings required',
            model: 'Local RAG',
            modelTag: 'Retrieval',
          },
        ],
        routingNote: 'Task: Document retrieval → Model: Local RAG',
      },
      {
        step: 3,
        activeModel: 'openai',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'What is our company policy on remote work?',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll search our internal documentation for the remote work policy. Let me query our knowledge base.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              'Retrieved from HR Handbook v3.2:\n\n**Remote Work Policy**\n\n• Employees can work remotely up to 3 days per week\n• Requires manager approval\n• Must be available during core hours (10am-3pm EST)\n• Quarterly in-person meetings required',
            model: 'Local RAG',
            modelTag: 'Retrieval',
          },
          {
            id: 4,
            role: 'assistant',
            content:
              '**Summary:**\n\nOur remote work policy allows up to 3 days per week remote with manager approval. Core hours (10am-3pm EST) must be maintained, and quarterly in-person meetings are mandatory.\n\nWould you like details on the approval process?',
            model: 'OpenAI',
            modelTag: 'Code',
          },
        ],
        routingNote: 'Task: Summary generation → Model: OpenAI',
      },
    ],
  },
  engineering: {
    models: [models.claude, models.openai, models.gemini],
    steps: [
      {
        step: 1,
        activeModel: 'claude',
        messages: [
          {
            id: 1,
            role: 'user',
            content:
              "I'm seeing a bug where users can't submit forms after the third attempt. The error says 'rate limit exceeded' but we don't have rate limiting on forms.",
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "This sounds like a state management issue. The error message is misleading - it's likely that form submission state isn't being reset properly after failed attempts. Let me analyze the codebase structure.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
        ],
        routingNote: 'Task: Bug analysis → Model: Claude',
      },
      {
        step: 2,
        activeModel: 'openai',
        messages: [
          {
            id: 1,
            role: 'user',
            content:
              "I'm seeing a bug where users can't submit forms after the third attempt. The error says 'rate limit exceeded' but we don't have rate limiting on forms.",
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "This sounds like a state management issue. The error message is misleading - it's likely that form submission state isn't being reset properly after failed attempts. Let me analyze the codebase structure.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content: 'Here\'s a patch to fix the form submission state:\n\n```typescript\n// Fix: Reset submission state on error\nconst handleSubmit = async () => {\n  setSubmitting(true)\n  try {\n    await submitForm()\n  } catch (error) {\n    setSubmitting(false) // Reset state\n    setError(error.message)\n  }\n}\n```',
            model: 'OpenAI',
            modelTag: 'Code',
            codeBlock: `const handleSubmit = async () => {\n  setSubmitting(true)\n  try {\n    await submitForm()\n  } catch (error) {\n    setSubmitting(false)\n    setError(error.message)\n  }\n}`,
          },
        ],
        routingNote: 'Task: Code generation → Model: OpenAI',
      },
      {
        step: 3,
        activeModel: 'openai',
        messages: [
          {
            id: 1,
            role: 'user',
            content:
              "I'm seeing a bug where users can't submit forms after the third attempt. The error says 'rate limit exceeded' but we don't have rate limiting on forms.",
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "This sounds like a state management issue. The error message is misleading - it's likely that form submission state isn't being reset properly after failed attempts. Let me analyze the codebase structure.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content: 'Here\'s a patch to fix the form submission state:\n\n```typescript\n// Fix: Reset submission state on error\nconst handleSubmit = async () => {\n  setSubmitting(true)\n  try {\n    await submitForm()\n  } catch (error) {\n    setSubmitting(false) // Reset state\n    setError(error.message)\n  }\n}\n```',
            model: 'OpenAI',
            modelTag: 'Code',
            codeBlock: `const handleSubmit = async () => {\n  setSubmitting(true)\n  try {\n    await submitForm()\n  } catch (error) {\n    setSubmitting(false)\n    setError(error.message)\n  }\n}`,
          },
          {
            id: 4,
            role: 'assistant',
            content:
              '**Test Cases:**\n\n1. Submit form successfully → state resets\n2. Submit form with error → state resets, error displayed\n3. Multiple rapid submissions → only one submission processes\n4. Network timeout → state resets, retry available',
            model: 'OpenAI',
            modelTag: 'Code',
          },
        ],
        routingNote: 'Task: Test generation → Model: OpenAI',
      },
      {
        step: 4,
        activeModel: 'gemini',
        messages: [
          {
            id: 1,
            role: 'user',
            content:
              "I'm seeing a bug where users can't submit forms after the third attempt. The error says 'rate limit exceeded' but we don't have rate limiting on forms.",
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "This sounds like a state management issue. The error message is misleading - it's likely that form submission state isn't being reset properly after failed attempts. Let me analyze the codebase structure.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content: 'Here\'s a patch to fix the form submission state:\n\n```typescript\n// Fix: Reset submission state on error\nconst handleSubmit = async () => {\n  setSubmitting(true)\n  try {\n    await submitForm()\n  } catch (error) {\n    setSubmitting(false) // Reset state\n    setError(error.message)\n  }\n}\n```',
            model: 'OpenAI',
            modelTag: 'Code',
            codeBlock: `const handleSubmit = async () => {\n  setSubmitting(true)\n  try {\n    await submitForm()\n  } catch (error) {\n    setSubmitting(false)\n    setError(error.message)\n  }\n}`,
          },
          {
            id: 4,
            role: 'assistant',
            content:
              '**Test Cases:**\n\n1. Submit form successfully → state resets\n2. Submit form with error → state resets, error displayed\n3. Multiple rapid submissions → only one submission processes\n4. Network timeout → state resets, retry available',
            model: 'OpenAI',
            modelTag: 'Code',
          },
          {
            id: 5,
            role: 'assistant',
            content:
              '**Architecture Diagram Prompt:**\n\n"A flowchart showing form submission flow: User Input → Validation → Submit Handler → API Call → Success/Error → State Reset. Highlight the error handling path that resets submission state."',
            model: 'Gemini',
            modelTag: 'Image',
            imagePreview: true,
          },
        ],
        routingNote: 'Task: Diagram generation → Model: Gemini',
      },
    ],
  },
  marketing: {
    models: [models.claude, models.gemini, models.openai],
    steps: [
      {
        step: 1,
        activeModel: 'claude',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Create a landing page hero for our new AI routing product.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll help you create a compelling landing page hero. Let me first understand your product's key value propositions and target audience.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
        ],
        routingNote: 'Task: Strategy → Model: Claude',
      },
      {
        step: 2,
        activeModel: 'gemini',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Create a landing page hero for our new AI routing product.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll help you create a compelling landing page hero. Let me first understand your product's key value propositions and target audience.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              '**Hero Copy:**\n\n"One Assistant. Every Model."\n\n"Route intelligently across OpenAI, Claude, Gemini, and more. One unified API, infinite possibilities."',
            model: 'Gemini',
            modelTag: 'Image',
          },
        ],
        routingNote: 'Task: Copy generation → Model: Gemini',
      },
      {
        step: 3,
        activeModel: 'gemini',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Create a landing page hero for our new AI routing product.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll help you create a compelling landing page hero. Let me first understand your product's key value propositions and target audience.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              '**Hero Copy:**\n\n"One Assistant. Every Model."\n\n"Route intelligently across OpenAI, Claude, Gemini, and more. One unified API, infinite possibilities."',
            model: 'Gemini',
            modelTag: 'Image',
          },
          {
            id: 4,
            role: 'assistant',
            content:
              '**Image Prompt:**\n\n"A futuristic AI routing interface with glowing neural network connections between multiple LLM nodes (OpenAI, Claude, Gemini), dark theme with emerald green accents, sleek and professional B2B aesthetic."',
            model: 'Gemini',
            modelTag: 'Image',
            imagePreview: true,
          },
        ],
        routingNote: 'Task: Image prompt → Model: Gemini',
      },
      {
        step: 4,
        activeModel: 'openai',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Create a landing page hero for our new AI routing product.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll help you create a compelling landing page hero. Let me first understand your product's key value propositions and target audience.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              '**Hero Copy:**\n\n"One Assistant. Every Model."\n\n"Route intelligently across OpenAI, Claude, Gemini, and more. One unified API, infinite possibilities."',
            model: 'Gemini',
            modelTag: 'Image',
          },
          {
            id: 4,
            role: 'assistant',
            content:
              '**Image Prompt:**\n\n"A futuristic AI routing interface with glowing neural network connections between multiple LLM nodes (OpenAI, Claude, Gemini), dark theme with emerald green accents, sleek and professional B2B aesthetic."',
            model: 'Gemini',
            modelTag: 'Image',
            imagePreview: true,
          },
          {
            id: 5,
            role: 'assistant',
            content:
              '**Brand Voice Rewrite:**\n\n"Unify Every Model. One Conversation."\n\n"Intelligent routing across OpenAI, Claude, Gemini, and beyond. Enterprise-grade AI orchestration in a single API."',
            model: 'OpenAI',
            modelTag: 'Code',
          },
        ],
        routingNote: 'Task: Brand voice → Model: OpenAI',
      },
    ],
  },
  analytics: {
    models: [models.local, models.openai, models.claude],
    steps: [
      {
        step: 1,
        activeModel: 'local',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Analyze this CSV of sales data and provide insights.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              'Processing CSV data... Analyzing 1,247 rows across 12 columns. Extracting key metrics and patterns.',
            model: 'Local RAG',
            modelTag: 'Retrieval',
            dataPreview: true,
          },
        ],
        routingNote: 'Task: Data processing → Model: Local RAG',
      },
      {
        step: 2,
        activeModel: 'openai',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Analyze this CSV of sales data and provide insights.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              'Processing CSV data... Analyzing 1,247 rows across 12 columns. Extracting key metrics and patterns.',
            model: 'Local RAG',
            modelTag: 'Retrieval',
            dataPreview: true,
          },
          {
            id: 3,
            role: 'assistant',
            content:
              '**Charts Generated:**\n\n• Revenue trend (line chart)\n• Product category breakdown (pie chart)\n• Regional performance (bar chart)\n• Monthly growth rate (area chart)',
            model: 'OpenAI',
            modelTag: 'Code',
            dataPreview: true,
          },
        ],
        routingNote: 'Task: Visualization → Model: OpenAI',
      },
      {
        step: 3,
        activeModel: 'claude',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Analyze this CSV of sales data and provide insights.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              'Processing CSV data... Analyzing 1,247 rows across 12 columns. Extracting key metrics and patterns.',
            model: 'Local RAG',
            modelTag: 'Retrieval',
            dataPreview: true,
          },
          {
            id: 3,
            role: 'assistant',
            content:
              '**Charts Generated:**\n\n• Revenue trend (line chart)\n• Product category breakdown (pie chart)\n• Regional performance (bar chart)\n• Monthly growth rate (area chart)',
            model: 'OpenAI',
            modelTag: 'Code',
            dataPreview: true,
          },
          {
            id: 4,
            role: 'assistant',
            content:
              '**Key Insights:**\n\n1. **Revenue Growth:** 23% YoY increase, strongest in Q4\n2. **Product Mix:** Software products now 45% of revenue (up from 32%)\n3. **Regional:** West Coast showing 40% growth, East Coast stable\n4. **Recommendation:** Focus marketing on software products in West Coast region',
            model: 'Claude',
            modelTag: 'Reasoning',
          },
        ],
        routingNote: 'Task: Analysis → Model: Claude',
      },
    ],
  },
  custom: {
    models: [models.claude, models.openai, models.gemini, models.ensemble],
    steps: [
      {
        step: 1,
        activeModel: 'claude',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Design a custom workflow that combines reasoning, code generation, and visualization.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll design a multi-step workflow that leverages different models for each task. Let me break this down into phases.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
        ],
        routingNote: 'Task: Planning → Model: Claude',
      },
      {
        step: 2,
        activeModel: 'openai',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Design a custom workflow that combines reasoning, code generation, and visualization.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll design a multi-step workflow that leverages different models for each task. Let me break this down into phases.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              '**Workflow Code:**\n\n```typescript\nconst workflow = {\n  step1: "Claude analyzes requirements",\n  step2: "OpenAI generates implementation",\n  step3: "Gemini creates visualizations",\n  step4: "Syntra Ensemble merges outputs"\n}\n```',
            model: 'OpenAI',
            modelTag: 'Code',
            codeBlock: `const workflow = {\n  step1: "Claude analyzes requirements",\n  step2: "OpenAI generates implementation",\n  step3: "Gemini creates visualizations",\n  step4: "Syntra Ensemble merges outputs"\n}`,
          },
        ],
        routingNote: 'Task: Implementation → Model: OpenAI',
      },
      {
        step: 3,
        activeModel: 'gemini',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Design a custom workflow that combines reasoning, code generation, and visualization.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll design a multi-step workflow that leverages different models for each task. Let me break this down into phases.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              '**Workflow Code:**\n\n```typescript\nconst workflow = {\n  step1: "Claude analyzes requirements",\n  step2: "OpenAI generates implementation",\n  step3: "Gemini creates visualizations",\n  step4: "Syntra Ensemble merges outputs"\n}\n```',
            model: 'OpenAI',
            modelTag: 'Code',
            codeBlock: `const workflow = {\n  step1: "Claude analyzes requirements",\n  step2: "OpenAI generates implementation",\n  step3: "Gemini creates visualizations",\n  step4: "Syntra Ensemble merges outputs"\n}`,
          },
          {
            id: 4,
            role: 'assistant',
            content:
              '**Visualization:**\n\nWorkflow diagram showing the orchestration of multiple models working together in sequence.',
            model: 'Gemini',
            modelTag: 'Image',
            imagePreview: true,
          },
        ],
        routingNote: 'Task: Visualization → Model: Gemini',
      },
      {
        step: 4,
        activeModel: 'ensemble',
        messages: [
          {
            id: 1,
            role: 'user',
            content: 'Design a custom workflow that combines reasoning, code generation, and visualization.',
          },
          {
            id: 2,
            role: 'assistant',
            content:
              "I'll design a multi-step workflow that leverages different models for each task. Let me break this down into phases.",
            model: 'Claude',
            modelTag: 'Reasoning',
          },
          {
            id: 3,
            role: 'assistant',
            content:
              '**Workflow Code:**\n\n```typescript\nconst workflow = {\n  step1: "Claude analyzes requirements",\n  step2: "OpenAI generates implementation",\n  step3: "Gemini creates visualizations",\n  step4: "Syntra Ensemble merges outputs"\n}\n```',
            model: 'OpenAI',
            modelTag: 'Code',
            codeBlock: `const workflow = {\n  step1: "Claude analyzes requirements",\n  step2: "OpenAI generates implementation",\n  step3: "Gemini creates visualizations",\n  step4: "Syntra Ensemble merges outputs"\n}`,
          },
          {
            id: 4,
            role: 'assistant',
            content:
              '**Visualization:**\n\nWorkflow diagram showing the orchestration of multiple models working together in sequence.',
            model: 'Gemini',
            modelTag: 'Image',
            imagePreview: true,
          },
          {
            id: 5,
            role: 'assistant',
            content:
              '**Unified Output:**\n\nCombining insights from Claude (requirements), OpenAI (implementation), and Gemini (visualization) into a cohesive workflow solution. All models contributed to this result within the same conversation context.',
            model: 'Syntra Ensemble',
            modelTag: 'Multi-Model',
          },
        ],
        routingNote: 'Task: Ensemble merge → Model: Syntra Ensemble',
      },
    ],
  },
}

const useCases = [
  {
    id: 'support',
    label: 'Support Automation',
    icon: Headphones,
    title: 'Resolve tickets faster with multi-model AI',
    description:
      'Claude analyzes complex issues, local RAG retrieves knowledge base articles, and OpenAI generates personalized responses—all in one conversation thread.',
    bullets: [
      'Complex reasoning for ticket analysis',
      'Knowledge base retrieval with local models',
      'Personalized response generation',
      'All models share the same context',
    ],
  },
  {
    id: 'knowledge',
    label: 'Internal Knowledge',
    icon: Database,
    title: 'Query your docs with intelligent routing',
    description:
      'Claude understands queries, local RAG searches documentation, and OpenAI summarizes results—seamlessly switching models while maintaining context.',
    bullets: [
      'Natural language query understanding',
      'Secure document retrieval',
      'Context-aware summarization',
      'Unified conversation history',
    ],
  },
  {
    id: 'engineering',
    label: 'Engineering / Code',
    icon: Code,
    title: 'Debug, code, test, and visualize in one flow',
    description:
      'Claude explains bugs, OpenAI generates patches and tests, Gemini creates diagrams—complete engineering workflows in a single chat thread.',
    bullets: [
      'Bug analysis with reasoning models',
      'Code generation and patches',
      'Test case creation',
      'Architectural diagram generation',
    ],
  },
  {
    id: 'marketing',
    label: 'Marketing & Creative',
    icon: ImageIcon,
    title: 'Create campaigns with multi-model collaboration',
    description:
      'Claude strategizes, Gemini writes copy and generates images, OpenAI refines brand voice—complete creative workflows orchestrated by Syntra.',
    bullets: [
      'Strategic planning and research',
      'Copy and content generation',
      'Image prompt creation',
      'Brand voice refinement',
    ],
  },
  {
    id: 'analytics',
    label: 'Data & Analytics',
    icon: TrendingUp,
    title: 'Analyze data with intelligent model routing',
    description:
      'Local models process data, OpenAI generates visualizations, Claude provides insights—complete analytics workflows in one conversation.',
    bullets: [
      'CSV and data processing',
      'Chart and visualization generation',
      'Insight extraction and analysis',
      'Recommendation generation',
    ],
  },
  {
    id: 'custom',
    label: 'Custom Workflows',
    icon: Settings,
    title: 'Build your own multi-model pipelines',
    description:
      'Combine any models in any sequence. Syntra orchestrates reasoning, code, images, and more—all within a single shared context window.',
    bullets: [
      'Custom model sequences',
      'Task-based routing',
      'Output merging and consensus',
      'Unlimited workflow combinations',
    ],
  },
]

export default function UseCasesPage() {
  const [activeTab, setActiveTab] = useState('support')

  const activeUseCase = useCases.find((uc) => uc.id === activeTab) || useCases[0]
  const activeDemo = useCaseDemos[activeTab as keyof typeof useCaseDemos]

  return (
    <div className="min-h-screen bg-[#020409]">
      {/* Hero Section */}
      

      {/* Metrics Strip */}
      

      {/* Use Cases Tabs */}
      <section className="py-16 md:py-24 border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2 md:grid-cols-3 lg:grid-cols-6 mb-16 bg-zinc-900/40 border border-white/10 rounded-xl h-auto p-1.5 gap-1.5">
              {useCases.map((useCase) => {
                const UseCaseIcon = useCase.icon
                return (
                  <TabsTrigger
                    key={useCase.id}
                    value={useCase.id}
                    className="flex flex-col items-center gap-2 data-[state=active]:bg-emerald-600 data-[state=active]:text-white data-[state=active]:shadow-lg data-[state=active]:shadow-emerald-500/20 py-3 px-2 rounded-lg transition-all"
                  >
                    <UseCaseIcon className="w-4 h-4" />
                    <span className="text-xs text-center leading-tight">{useCase.label}</span>
                  </TabsTrigger>
                )
              })}
            </TabsList>

            {useCases.map((useCase) => {
              const UseCaseIcon = useCase.icon
              const demo = useCaseDemos[useCase.id as keyof typeof useCaseDemos]

              return (
                <TabsContent key={useCase.id} value={useCase.id} className="space-y-16 mt-8">
                  {/* Use Case Header */}
                  
                    <div className="text-center space-y-6 max-w-4xl mx-auto">
                      <div className="flex justify-center">
                        <motion.div
                          className="w-16 h-16 rounded-xl bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30"
                          animate={{ scale: [0.98, 1, 0.98] }}
                          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                        >
                          <UseCaseIcon className="w-8 h-8 text-emerald-400" />
                        </motion.div>
                      </div>
                      <h2 className="text-3xl md:text-4xl font-bold text-foreground">
                        {useCase.title}
                      </h2>
                      <p className="text-lg text-muted-foreground leading-relaxed">
                        {useCase.description}
                      </p>
                    </div>
                  

                  {/* Two Column Layout: Description + Demo */}
                  <div className="grid lg:grid-cols-2 gap-8 lg:gap-12 items-start">
                    {/* Left: Bullets */}
                    
                      <div className="space-y-6 lg:sticky lg:top-24">
                        <h3 className="text-lg font-semibold text-foreground mb-6">Key Features</h3>
                        <ul className="space-y-3">
                          {useCase.bullets.map((bullet, index) => (
                            <motion.li
                              key={index}
                              initial={{ opacity: 0, x: -20 }}
                              whileInView={{ opacity: 1, x: 0 }}
                              viewport={{ once: true }}
                              transition={{ duration: 0.4, delay: index * 0.1 }}
                              className="flex items-start gap-3"
                            >
                              <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                              </div>
                              <span className="text-sm text-muted-foreground leading-relaxed">{bullet}</span>
                            </motion.li>
                          ))}
                        </ul>
                      </div>
                    

                    {/* Right: Animated Demo */}
                    
                      <div className="lg:sticky lg:top-24">
                        <UseCaseDemo steps={demo.steps} models={demo.models} />
                      </div>
                    
                  </div>
                </TabsContent>
              )
            })}
          </Tabs>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-16 md:py-24 bg-gradient-to-b from-zinc-900/40 to-[#020409]">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="space-y-6"
            >
              <h2 className="text-3xl md:text-4xl font-bold text-foreground">
                Ready to unify your workflows?
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Start using Syntra today and experience the power of multi-model collaboration in a
                single conversation.
              </p>
              <div className="flex items-center justify-center gap-4 pt-4">
                <Link href="/conversations">
                  <Button
                    size="lg"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white h-12 px-8"
                  >
                    Open Chat
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </Link>
                <Link href="/pricing">
                  <Button size="lg" variant="outline" className="h-12 px-8">
                    View Pricing
                  </Button>
                </Link>
              </div>
            </motion.div>
          
        </div>
      </section>
    </div>
  )
}
