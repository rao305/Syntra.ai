'use client'

import * as React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Route,
  Shield,
  Zap,
  BarChart3,
  ArrowRight,
  Code2,
  Image as ImageIcon,
  Brain,
  Key,
  Eye,
  Users,
  MessageSquare,
  Sparkles,
} from 'lucide-react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import Reveal from '@/components/motion/Reveal'
import Stagger, { item } from '@/components/motion/Stagger'
import { MetricsStrip } from '@/components/metrics-strip'
import { HeroMultiModelDemo } from '@/components/hero-multi-model-demo'
import { SectionHeader } from '@/components/section-header'
import { FeatureCard } from '@/components/feature-card'
import { DifferentiatorCard } from '@/components/differentiator-card'

export default function ProductPage() {
  return (
    <div className="min-h-screen bg-[#020409]">
      {/* Hero Section with Multi-Model Demo */}
      <section className="relative border-b border-white/10 bg-gradient-to-b from-[#020409] via-[#050810] to-[#020409] overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(34,197,94,0.1),transparent_50%)]" />
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 md:py-24 relative">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Column - Text */}
            <Reveal>
              <div className="space-y-6">
                <motion.p
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-sm font-semibold text-emerald-400 uppercase tracking-wider"
                >
                  Operate across LLMs
                </motion.p>
                <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-100 tracking-tight">
                  One assistant.
                  <br />
                  <span className="text-emerald-400">Every model.</span>
                </h1>
                <p className="text-lg md:text-xl text-slate-300 max-w-xl">
                  Syntra lets you chat once while OpenAI, Claude, Gemini, and more collaborate behind
                  the scenes in the same context window.
                </p>
                <div className="flex items-center gap-4 pt-4">
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
                      See Pricing
                    </Button>
                  </Link>
                </div>
              </div>
            </Reveal>

            {/* Right Column - Multi-Model Demo */}
            <Reveal delay={0.2}>
              <div className="relative">
                <HeroMultiModelDemo />
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Metrics Strip */}
      <MetricsStrip />

      {/* Logos / Social Proof */}
      <section className="py-12 border-b border-white/10 bg-zinc-900/20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Reveal>
            <p className="text-center text-sm text-muted-foreground mb-6 uppercase tracking-wider">
              Used by leading teams
            </p>
            <div className="flex items-center justify-center gap-8 md:gap-12 flex-wrap opacity-60">
              {['Acme Corp', 'TechStart', 'DataFlow', 'CloudScale', 'AI Labs'].map(
                (logo, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 0.6 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.4, delay: idx * 0.1 }}
                    className="text-sm font-medium text-muted-foreground"
                  >
                    {logo}
                  </motion.div>
                ),
              )}
            </div>
          </Reveal>
        </div>
      </section>

      {/* How Syntra Works */}
      <section className="py-16 md:py-24 border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeader
            title="How Syntra works"
            subtitle="Syntra sits between your users and multiple models, keeping one shared context and picking the right model for each task."
          />

          <Stagger>
            <div className="relative max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-5 gap-6 items-center">
                {/* User */}
                <motion.div variants={item} className="text-center space-y-3">
                  <motion.div
                    className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center border-2 border-blue-500/30"
                    whileHover={{ scale: 1.05 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                  >
                    <Users className="w-8 h-8 text-blue-400" />
                  </motion.div>
                  <div className="font-semibold text-foreground">User Chat</div>
                </motion.div>

                {/* Arrow */}
                <motion.div variants={item} className="hidden md:block">
                  <ArrowRight className="w-8 h-8 text-emerald-400 mx-auto" />
                </motion.div>

                {/* Syntra Orchestrator */}
                <motion.div variants={item} className="text-center space-y-3">
                  <motion.div
                    className="w-24 h-24 mx-auto rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center border-2 border-emerald-500/30 ring-4 ring-emerald-500/10"
                    whileHover={{ scale: 1.05 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                  >
                    <Sparkles className="w-10 h-10 text-emerald-400" />
                  </motion.div>
                  <div className="font-semibold text-foreground">Syntra Orchestrator</div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <div>Shared context window</div>
                    <div>Routing policies</div>
                    <div>Model collaboration</div>
                  </div>
                </motion.div>

                {/* Arrow */}
                <motion.div variants={item} className="hidden md:block">
                  <ArrowRight className="w-8 h-8 text-emerald-400 mx-auto" />
                </motion.div>

                {/* Model Row */}
                <motion.div variants={item} className="text-center space-y-3">
                  <div className="flex items-center justify-center gap-2 flex-wrap">
                    {['OpenAI', 'Claude', 'Gemini', 'OSS', 'Local'].map((model, idx) => (
                      <div
                        key={idx}
                        className="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-xs text-muted-foreground"
                      >
                        {model}
                      </div>
                    ))}
                  </div>
                  <div className="font-semibold text-foreground">Model Row</div>
                </motion.div>
              </div>
            </div>
          </Stagger>
        </div>
      </section>

      {/* Core Features */}
      <section className="py-16 md:py-24 border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeader
            title="Core Features"
            subtitle="Everything you need to operate AI at scale across multiple models"
          />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              icon={MessageSquare}
              title="Shared Context Across Models"
              description="Maintain conversation history and context when switching between different LLM providers seamlessly."
              features={[
                'Unified conversation thread',
                'Context preservation across providers',
                'Multi-model memory management',
                'Seamless model transitions',
              ]}
              color="emerald"
              delay={0}
            />
            <FeatureCard
              icon={Route}
              title="Smart Routing Engine"
              description="Automatically selects the best model for each task based on intent, performance, and cost."
              features={[
                'Intent-based routing',
                'Real-time performance monitoring',
                'Automatic fallback chains',
                'Cost-aware routing policies',
              ]}
              color="blue"
              delay={0.1}
            />
            <FeatureCard
              icon={Sparkles}
              title="Model Collaboration / Ensembles"
              description="Combine outputs from multiple models to get the best results for complex tasks."
              features={[
                'Multi-model ensemble responses',
                'Output reconciliation',
                'Confidence scoring',
                'Task-specific model selection',
              ]}
              color="purple"
              delay={0.2}
            />
            <FeatureCard
              icon={Zap}
              title="Unified API & SDKs"
              description="One consistent interface across all providers. No more vendor lock-in or API fragmentation."
              features={[
                'Single API endpoint',
                'Standardized request/response',
                'Streaming support',
                'Type-safe SDKs (TypeScript, Python)',
              ]}
              color="orange"
              delay={0.3}
            />
            <FeatureCard
              icon={Key}
              title="Secure Key Vault"
              description="Enterprise-grade security for API keys with encryption at rest and in transit."
              features={[
                'Encrypted key storage',
                'Per-organization isolation',
                'Audit logs',
                'SOC 2 compliant',
              ]}
              color="green"
              delay={0.4}
            />
            <FeatureCard
              icon={BarChart3}
              title="Observability & Cost Control"
              description="Real-time metrics, cost tracking, and performance analytics across all providers."
              features={[
                'Token usage tracking',
                'Latency & TTFT metrics',
                'Cost per query analysis',
                'Provider health monitoring',
              ]}
              color="teal"
              delay={0.5}
            />
          </div>
        </div>
      </section>

      {/* What Makes Syntra Different */}
      <section className="py-16 md:py-24 border-b border-white/10 bg-zinc-900/20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeader
            title="What Makes Syntra Different"
            subtitle="The only platform that truly unifies multiple LLMs into one assistant"
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <DifferentiatorCard
              icon={MessageSquare}
              title="One chat, many models"
              description="Swap providers without losing the thread. Your conversation history stays intact as you switch between OpenAI, Claude, Gemini, and more—all in the same context window."
              delay={0}
            />
            <DifferentiatorCard
              icon={Route}
              title="Right model for every task"
              description="Syntra automatically routes reasoning tasks to Claude, code generation to OpenAI, image tasks to Gemini, and more—all within the same conversation flow."
              delay={0.1}
            />
            <DifferentiatorCard
              icon={Shield}
              title="Production-grade reliability & security"
              description="100% uptime SLA, 200ms p95 TTFT, and SOC 2 ready. Built for enterprise with the reliability and security your business demands."
              delay={0.2}
            />
            <DifferentiatorCard
              icon={Key}
              title="Vendor-neutral & future-proof"
              description="Bring your own keys, use proprietary and open-source models, and swap providers anytime. No lock-in, complete control over your AI infrastructure."
              delay={0.3}
            />
          </div>
        </div>
      </section>

      {/* Use Cases Preview */}
      <section className="py-16 md:py-24 border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeader
            title="Use Cases"
            subtitle="See how teams use Syntra to operate across multiple LLMs"
          />

          <Stagger>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  icon: Brain,
                  title: 'Customer Support',
                  description:
                    'Route complex queries to reasoning models, code issues to coding models, all in one thread.',
                },
                {
                  icon: Code2,
                  title: 'Development',
                  description:
                    'Get code suggestions from OpenAI, explanations from Claude, and documentation from Gemini.',
                },
                {
                  icon: ImageIcon,
                  title: 'Content Creation',
                  description:
                    'Generate images with Gemini, write copy with Claude, and optimize with OpenAI—seamlessly.',
                },
                {
                  icon: Zap,
                  title: 'Research & Analysis',
                  description:
                    'Combine multiple models to analyze data, generate insights, and create comprehensive reports.',
                },
              ].map((useCase, idx) => {
                const Icon = useCase.icon
                return (
                  <motion.div key={idx} variants={item}>
                    <Card className="border-white/5 bg-zinc-900/40 backdrop-blur-sm hover:bg-zinc-900/60 transition-all hover:-translate-y-1 h-full">
                      <CardContent className="p-6">
                        <div className="w-12 h-12 rounded-lg bg-emerald-500/20 flex items-center justify-center mb-4">
                          <Icon className="w-6 h-6 text-emerald-400" />
                        </div>
                        <h3 className="text-lg font-semibold text-foreground mb-2">
                          {useCase.title}
                        </h3>
                        <p className="text-sm text-muted-foreground">{useCase.description}</p>
                      </CardContent>
                    </Card>
                  </motion.div>
                )
              })}
            </div>
          </Stagger>

          <div className="text-center mt-12">
            <Link href="/use-cases">
              <Button variant="outline" size="lg">
                Explore All Use Cases
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-16 md:py-24 border-b border-white/10 bg-zinc-900/20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeader
            title="What Our Users Say"
            subtitle="See how teams are transforming their AI workflows with Syntra"
          />

          <Stagger>
            <div className="grid md:grid-cols-3 gap-6">
              {[
                {
                  quote:
                    "Syntra transformed how we work with AI. We can now use Claude for strategy, OpenAI for code, and Gemini for images—all in the same conversation. Game changer.",
                  author: 'Sarah Chen',
                  role: 'CTO, TechStart',
                },
                {
                  quote:
                    "The shared context window is incredible. We switch models mid-conversation without losing any context. It's like having one super-powered assistant.",
                  author: 'Michael Rodriguez',
                  role: 'Head of AI, DataFlow',
                },
                {
                  quote:
                    "Production-grade reliability with the flexibility to use any model. Syntra gives us the best of both worlds—enterprise reliability and vendor freedom.",
                  author: 'Emily Watson',
                  role: 'VP Engineering, CloudScale',
                },
              ].map((testimonial, idx) => (
                <motion.div key={idx} variants={item}>
                  <Card className="border-white/5 bg-zinc-900/40 backdrop-blur-sm h-full">
                    <CardContent className="p-6">
                      <div className="mb-4">
                        <div className="flex gap-1 mb-2">
                          {[...Array(5)].map((_, i) => (
                            <span key={i} className="text-emerald-400">
                              ★
                            </span>
                          ))}
                        </div>
                        <p className="text-sm text-muted-foreground italic">
                          "{testimonial.quote}"
                        </p>
                      </div>
                      <div className="pt-4 border-t border-white/5">
                        <p className="text-sm font-semibold text-foreground">
                          {testimonial.author}
                        </p>
                        <p className="text-xs text-muted-foreground">{testimonial.role}</p>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </Stagger>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-16 md:py-24 bg-gradient-to-b from-zinc-900/40 to-[#020409]">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          <Reveal>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="space-y-6"
            >
              <h2 className="text-3xl md:text-4xl font-bold text-foreground">
                Ready to operate across LLMs?
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Start chatting with Syntra today. Experience the power of one assistant that can
                leverage every model.
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
          </Reveal>
        </div>
      </section>
    </div>
  )
}
