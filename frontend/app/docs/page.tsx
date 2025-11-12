'use client'

import * as React from 'react'
import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Search, Book, Code, Key, Webhook, Shield, Rocket, ArrowRight } from 'lucide-react'
import Link from 'next/link'

const docSections = [
  {
    id: 'quickstart',
    title: 'Quickstart',
    icon: Rocket,
    description: 'Get up and running in 5 minutes',
    content: 'Learn how to make your first API call and start using DAC.',
  },
  {
    id: 'auth',
    title: 'Authentication',
    icon: Key,
    description: 'API keys and security',
    content: 'Understand how to authenticate requests and manage API keys securely.',
  },
  {
    id: 'chat',
    title: 'Chat API',
    icon: Code,
    description: 'Send messages and receive responses',
    content: 'Complete reference for the chat endpoint, including request/response formats.',
  },
  {
    id: 'streaming',
    title: 'Streaming',
    icon: Code,
    description: 'Real-time response streaming',
    content: 'Implement streaming responses for better user experience and lower latency.',
  },
  {
    id: 'webhooks',
    title: 'Webhooks',
    icon: Webhook,
    description: 'Event notifications',
    content: 'Set up webhooks to receive real-time notifications about events in your account.',
  },
  {
    id: 'sdk',
    title: 'SDKs',
    icon: Code,
    description: 'Client libraries',
    content: 'Use our official SDKs for Python, TypeScript, and other languages.',
  },
  {
    id: 'security',
    title: 'Security',
    icon: Shield,
    description: 'Best practices and compliance',
    content: 'Learn about our security measures, compliance certifications, and best practices.',
  },
]

export default function DocsPage() {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredSections = docSections.filter(
    (section) =>
      section.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      section.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="border-b border-border bg-zinc-900/60 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center space-y-6">
            <div className="flex justify-center">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 flex items-center justify-center border-2 border-emerald-500/30">
                <Book className="w-8 h-8 text-emerald-400" />
              </div>
            </div>
            <h1 className="text-5xl font-bold text-foreground tracking-tight">
              Developer Documentation
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Everything you need to integrate DAC into your application
            </p>
          </div>
        </div>
      </section>

      {/* Search and Content */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl mx-auto mb-12">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search documentation..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-zinc-900/40 border-border"
              />
            </div>
          </div>

          {/* Documentation Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredSections.map((section) => {
              const Icon = section.icon
              return (
                <Card
                  key={section.id}
                  className="border-border bg-zinc-900/40 backdrop-blur-sm hover:bg-zinc-900/60 transition-colors cursor-pointer group"
                >
                  <Link href={`/docs/${section.id}`}>
                    <CardContent className="p-6">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-lg bg-emerald-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-emerald-500/30 transition-colors">
                          <Icon className="w-6 h-6 text-emerald-400" />
                        </div>
                        <div className="flex-1 space-y-2">
                          <h3 className="text-lg font-semibold text-foreground group-hover:text-emerald-400 transition-colors">
                            {section.title}
                          </h3>
                          <p className="text-sm text-muted-foreground">{section.description}</p>
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {section.content}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity">
                            Read more
                            <ArrowRight className="w-3 h-3" />
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Link>
                </Card>
              )
            })}
          </div>

          {/* Quick Links */}
          <div className="mt-16 pt-16 border-t border-border">
            <h2 className="text-2xl font-bold text-foreground mb-8 text-center">
              Popular Guides
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl mx-auto">
              <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
                <CardContent className="p-6">
                  <h3 className="font-semibold text-foreground mb-2">Getting Started</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    New to DAC? Start here to learn the basics.
                  </p>
                  <Link href="/docs/quickstart">
                    <Button variant="ghost" size="sm">
                      View Guide
                      <ArrowRight className="ml-2 w-4 h-4" />
                    </Button>
                  </Link>
                </CardContent>
              </Card>
              <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
                <CardContent className="p-6">
                  <h3 className="font-semibold text-foreground mb-2">API Reference</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Complete API documentation with examples.
                  </p>
                  <Link href="/docs/chat">
                    <Button variant="ghost" size="sm">
                      View Reference
                      <ArrowRight className="ml-2 w-4 h-4" />
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 border-t border-border bg-zinc-900/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-foreground mb-4">
            Need help getting started?
          </h2>
          <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
            Our developer support team is here to help you integrate DAC successfully.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/">
              <Button size="lg" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                Try It Now
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
            <Link href="/contact">
              <Button size="lg" variant="outline">
                Contact Support
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

