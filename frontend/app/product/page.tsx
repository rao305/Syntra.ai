'use client'

import * as React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Route, Shield, Zap, BarChart3, ArrowRight } from 'lucide-react'
import Link from 'next/link'

export default function ProductPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="border-b border-border bg-zinc-900/60 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center space-y-6">
            <h1 className="text-5xl font-bold text-foreground tracking-tight">
              Operate across LLMs.
              <br />
              <span className="text-emerald-400">One unified assistant.</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              DAC routes your queries intelligently across OpenAI, Anthropic, Gemini, and more.
              Get the best response, every time.
            </p>
            <div className="flex items-center justify-center gap-4 pt-4">
              <Link href="/">
                <Button size="lg" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                  Open Chat
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
              <Link href="/pricing">
                <Button size="lg" variant="outline">
                  See Pricing
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture Diagram */}
      <section className="py-16 border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground mb-4">How It Works</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Your queries flow through DAC's intelligent routing layer to the optimal provider
            </p>
          </div>
          
          <div className="relative max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-6 items-center">
              {/* User */}
              <div className="text-center space-y-3">
                <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center border-2 border-blue-500/30">
                  <span className="text-2xl">👤</span>
                </div>
                <div className="font-semibold text-foreground">User</div>
              </div>

              {/* Arrow */}
              <div className="hidden md:block">
                <ArrowRight className="w-8 h-8 text-emerald-400 mx-auto" />
              </div>

              {/* DAC */}
              <div className="text-center space-y-3">
                <div className="w-24 h-24 mx-auto rounded-2xl bg-gradient-to-br from-emerald-500/20 to-blue-500/20 flex items-center justify-center border-2 border-emerald-500/30 ring-4 ring-emerald-500/10">
                  <span className="text-3xl font-bold text-emerald-400">DAC</span>
                </div>
                <div className="font-semibold text-foreground">Smart Router</div>
              </div>

              {/* Arrow */}
              <div className="hidden md:block">
                <ArrowRight className="w-8 h-8 text-emerald-400 mx-auto" />
              </div>

              {/* Providers */}
              <div className="text-center space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="w-16 h-16 rounded-xl bg-green-500/20 flex items-center justify-center border border-green-500/30">
                    <span className="text-lg">🤖</span>
                  </div>
                  <div className="w-16 h-16 rounded-xl bg-purple-500/20 flex items-center justify-center border border-purple-500/30">
                    <span className="text-lg">🧠</span>
                  </div>
                  <div className="w-16 h-16 rounded-xl bg-blue-500/20 flex items-center justify-center border border-blue-500/30">
                    <span className="text-lg">💎</span>
                  </div>
                  <div className="w-16 h-16 rounded-xl bg-orange-500/20 flex items-center justify-center border border-orange-500/30">
                    <span className="text-lg">⚡</span>
                  </div>
                </div>
                <div className="font-semibold text-foreground">LLM Providers</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Cards */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground mb-4">Core Features</h2>
            <p className="text-muted-foreground">
              Everything you need to operate AI at scale
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Smart Routing */}
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm hover:bg-zinc-900/60 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-emerald-500/20 flex items-center justify-center mb-4">
                  <Route className="w-6 h-6 text-emerald-400" />
                </div>
                <CardTitle className="text-xl">Smart Routing</CardTitle>
                <CardDescription>
                  Automatically selects the best LLM provider based on query intent, latency requirements, and cost optimization.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Intent-based provider selection</li>
                  <li>• Real-time performance monitoring</li>
                  <li>• Automatic fallback chains</li>
                  <li>• Cost-aware routing policies</li>
                </ul>
              </CardContent>
            </Card>

            {/* Unified API */}
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm hover:bg-zinc-900/60 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center mb-4">
                  <Zap className="w-6 h-6 text-blue-400" />
                </div>
                <CardTitle className="text-xl">Unified API</CardTitle>
                <CardDescription>
                  One consistent interface across all providers. No more vendor lock-in or API fragmentation.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Single API endpoint</li>
                  <li>• Standardized request/response format</li>
                  <li>• Streaming support</li>
                  <li>• Type-safe SDKs</li>
                </ul>
              </CardContent>
            </Card>

            {/* Secure Vault */}
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm hover:bg-zinc-900/60 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center mb-4">
                  <Shield className="w-6 h-6 text-purple-400" />
                </div>
                <CardTitle className="text-xl">Secure Vault</CardTitle>
                <CardDescription>
                  Enterprise-grade security for API keys, with encryption at rest and in transit.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Encrypted key storage</li>
                  <li>• Per-organization isolation</li>
                  <li>• Audit logs</li>
                  <li>• SOC 2 compliant</li>
                </ul>
              </CardContent>
            </Card>

            {/* Observability Dashboard */}
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm hover:bg-zinc-900/60 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-orange-500/20 flex items-center justify-center mb-4">
                  <BarChart3 className="w-6 h-6 text-orange-400" />
                </div>
                <CardTitle className="text-xl">Observability Dashboard</CardTitle>
                <CardDescription>
                  Real-time metrics, cost tracking, and performance analytics across all providers.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Token usage tracking</li>
                  <li>• Latency & TTFT metrics</li>
                  <li>• Cost per query analysis</li>
                  <li>• Provider health monitoring</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 border-t border-border bg-zinc-900/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-foreground mb-4">
            Ready to get started?
          </h2>
          <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
            Start chatting with DAC today. No credit card required.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/">
              <Button size="lg" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                Open Chat
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
            <Link href="/pricing">
              <Button size="lg" variant="outline">
                View Pricing
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

