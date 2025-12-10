'use client'

import * as React from 'react'
import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Book,
  Code,
  Key,
  Webhook,
  Shield,
  Rocket,
  ArrowRight,
  Terminal,
  Route,
  MessageSquare,
  Copy,
  Check,
} from 'lucide-react'
import Link from 'next/link'
import { motion } from 'framer-motion'

const docSections = [
  {
    id: 'quickstart',
    title: 'Quickstart',
    icon: Rocket,
    description: 'Get up and running in 5 minutes',
    color: 'text-emerald-400',
  },
  {
    id: 'auth',
    title: 'Authentication',
    icon: Key,
    description: 'API keys and security',
    color: 'text-blue-400',
  },
  {
    id: 'chat',
    title: 'Chat API',
    icon: MessageSquare,
    description: 'Send messages and receive responses',
    color: 'text-purple-400',
  },
  {
    id: 'routing',
    title: 'Routing Policies',
    icon: Route,
    description: 'Configure intelligent routing',
    color: 'text-orange-400',
  },
  {
    id: 'webhooks',
    title: 'Webhooks',
    icon: Webhook,
    description: 'Event notifications',
    color: 'text-pink-400',
  },
  {
    id: 'streaming',
    title: 'Streaming',
    icon: Terminal,
    description: 'Real-time response streaming',
    color: 'text-cyan-400',
  },
  {
    id: 'sdk',
    title: 'SDKs',
    icon: Code,
    description: 'Client libraries',
    color: 'text-green-400',
  },
  {
    id: 'context',
    title: 'Multi-Model Context',
    icon: MessageSquare,
    description: 'Shared context across models',
    color: 'text-emerald-400',
    highlight: true,
  },
]

const codeSamples = [
  {
    language: 'typescript',
    code: `const response = await client.chat({
  messages: [{ role: 'user', content: 'Hello' }]
})`,
  },
  {
    language: 'python',
    code: `response = client.chat(
    messages=[{"role": "user", "content": "Hello"}]
)`,
  },
]

export default function DocsPage() {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

  const handleCopy = (index: number, code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  return (
    <div className="min-h-screen bg-[#020409]">
      {/* Hero Section with Live API Simulation */}
      <section className="relative border-b border-white/10 bg-gradient-to-b from-[#020409] via-[#050810] to-[#020409] overflow-hidden py-16 md:py-24">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(34,197,94,0.1),transparent_50%)]" />
        
        {/* Grid Background */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(rgba(34, 197, 94, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(34, 197, 94, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
          }}
        />

        <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="text-center space-y-6 mb-12">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-100 tracking-tight">
                Developer Documentation
              </h1>
              <p className="text-lg md:text-xl text-slate-300 max-w-3xl mx-auto">
                Learn how to use multiple LLMs in one continuous context window.
              </p>
            </div>
        </div>
      </section>

      {/* Metrics Strip */}

      {/* Quickstart Cards */}
      <section className="py-16 md:py-24 border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Reveal>
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
                Documentation Sections
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Everything you need to build with Syntra
              </p>
            </div>
          </Reveal>

          <Stagger>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {docSections.map((section, index) => {
                const Icon = section.icon
                return (
                  <motion.div key={section.id} variants={item}>
                    <Card
                      className={`border-white/10 bg-zinc-900/40 backdrop-blur-sm hover:bg-zinc-900/60 transition-all hover:-translate-y-1 cursor-pointer group h-full ${
                        section.highlight ? 'border-emerald-500/50 shadow-lg shadow-emerald-500/10' : ''
                      }`}
                    >
                      <Link href={`/docs/${section.id}`}>
                        <CardContent className="p-6">
                          <div className="space-y-4">
                            <motion.div
                              className={`w-12 h-12 rounded-lg bg-emerald-500/20 flex items-center justify-center group-hover:bg-emerald-500/30 transition-colors ${
                                section.highlight ? 'ring-2 ring-emerald-500/50' : ''
                              }`}
                              whileHover={{ scale: 1.05 }}
                            >
                              <Icon className={`w-6 h-6 ${section.color}`} />
                            </motion.div>
                            <div>
                              <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-emerald-400 transition-colors">
                                {section.title}
                                {section.highlight && (
                                  <span className="ml-2 text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">
                                    Special
                                  </span>
                                )}
                              </h3>
                              <p className="text-sm text-muted-foreground">{section.description}</p>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity">
                              Read more
                              <ArrowRight className="w-3 h-3" />
                            </div>
                          </div>
                        </CardContent>
                      </Link>
                    </Card>
                  </motion.div>
                )
              })}
            </div>
          </Stagger>
        </div>
      </section>

      {/* API Reference Preview */}
      <section className="py-16 md:py-24 border-b border-white/10 bg-zinc-900/20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Reveal>
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
                API Reference
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Simple, powerful API for multi-model conversations
              </p>
            </div>
          </Reveal>

          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {codeSamples.map((sample, index) => (
              <Reveal key={index} delay={index * 0.1}>
                <Card className="border-white/10 bg-zinc-900/80 backdrop-blur-xl rounded-xl overflow-hidden">
                  <div className="bg-zinc-950/50 border-b border-white/5 px-4 py-3 flex items-center justify-between">
                    <span className="text-xs text-muted-foreground font-mono uppercase">
                      {sample.language}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopy(index, sample.code)}
                      className="h-7 px-2 text-xs"
                    >
                      {copiedIndex === index ? (
                        <>
                          <Check className="w-3 h-3 mr-1 text-emerald-400" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3 mr-1" />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                  <div className="p-4">
                    <motion.pre
                      initial={{ opacity: 0 }}
                      whileInView={{ opacity: 1 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.5, delay: index * 0.2 }}
                      className="font-mono text-xs text-emerald-300/90 overflow-x-auto"
                    >
                      {sample.code}
                    </motion.pre>
                  </div>
                </Card>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Routing Visualizer & Model Switching */}
      <section className="py-16 md:py-24 border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Reveal>
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
                See Syntra in Action
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Visualize how Syntra routes messages and switches models in real-time
              </p>
            </div>
          </Reveal>

          <div className="grid lg:grid-cols-2 gap-8">
            <Reveal delay={0.2}>
              <RoutingVisualizer />
            </Reveal>
            <Reveal delay={0.4}>
              <ModelSwitchingSim />
            </Reveal>
          </div>
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
                Ready to build with Syntra?
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Start integrating multiple LLMs into your application today.
              </p>
              <div className="flex items-center justify-center gap-4 pt-4">
                <Link href="/conversations">
                  <Button
                    size="lg"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white h-12 px-8"
                  >
                    Try It Now
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </Link>
                <Link href="/contact">
                  <Button size="lg" variant="outline" className="h-12 px-8">
                    Contact Support
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
