"use client"

import { ArrowRight, Brain, Lock, Sparkles, Zap } from "lucide-react"
import Image from "next/image"
import type React from "react"
import { useEffect, useRef, useState } from "react"

export function FeaturesSection() {
  const [isVisible, setIsVisible] = useState(false)
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      { threshold: 0.1 }
    )

    if (sectionRef.current) {
      observer.observe(sectionRef.current)
    }

    return () => observer.disconnect()
  }, [])

  return (
    <section ref={sectionRef} className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <h2 className={`text-3xl md:text-4xl lg:text-5xl font-bold text-foreground text-center mb-4 transition-all duration-1000 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}>
          Your Old AI Stack vs Syntra
        </h2>
        <p className={`text-muted-foreground text-center max-w-3xl mx-auto mb-16 transition-all duration-1000 delay-200 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}>
          Before: multiple tools, multiple subscriptions, scattered context. After: one private workspace that
          orchestrates them all.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          {/* Left Column - Before: Your AI tool stack */}
          <div className={`bg-card rounded-xl border border-border p-6 transition-all duration-1000 delay-300 ${isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-8'
            }`}>
            <h3 className="text-xl font-semibold text-foreground mb-6 flex items-center gap-2">
              <span className="text-muted-foreground">Before:</span> Your AI tool stack
            </h3>

            <div className="space-y-3">
              <StackRow role="Planning & strategy" model="Grok-1.5" iconSrc="/images/grok-v2.jpg" iconInvert />
              <StackRow role="Frontend UI & styling" model="Gemini Pro" iconSrc="/images/new-gemini-icon-cover.webp" />
              <StackRow role="Backend & APIs" model="Claude 3.5 Sonnet" iconSrc="/images/claude-ai-symbol.png" />
              <StackRow role="Writing tests" model="GPT-4.1" iconSrc="/images/chatgpt.jpg" iconInvert />
              <StackRow role="Running tests & CI help" model="GPT-4.1" iconSrc="/images/chatgpt.jpg" iconInvert />
              <StackRow role="Debugging & refactors" model="Claude 3 Opus" iconSrc="/images/claude-ai-symbol.png" />
              <StackRow
                role="Deep web research"
                model="Perplexity AI"
                iconSrc="/images/frtnglxvs-ls6kpr2g1pfj1sne4lq4lqkk-nobmk3uw6nokd0v5lle-o84uizwufj-qb25f-3dhegaa-dag4aamnwnoczt35j2wcc3ogai5jzm3rnhmec7r2rdt3ttxfh3-dzi1na0kjtxfw82solq.png"
              />
            </div>

            <div className="mt-6 pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground">
                7 different tools. 7 different subscriptions. Context scattered everywhere.
              </p>
            </div>
          </div>

          {/* Right Column - After: Syntra AI */}
          <div className={`relative bg-gradient-to-br from-card to-card rounded-xl border-2 border-primary/50 p-6 shadow-lg shadow-primary/10 transition-all duration-1000 delay-500 hover:scale-[1.02] hover:shadow-xl hover:shadow-primary/20 ${isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-8'
            }`}>
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent rounded-xl pointer-events-none animate-pulse" style={{ animationDuration: '3s' }} />

            <div className="relative">
              <h3 className="text-xl font-semibold text-foreground mb-2 flex items-center gap-2">
                <span className="text-muted-foreground">After:</span> Syntra AI
              </h3>

              <h4 className="text-2xl font-bold text-foreground mb-4">One Workspace to Orchestrate Them All</h4>

              <p className="text-muted-foreground mb-4">
                Instead of juggling separate tools for planning, coding, testing, debugging, and research, Syntra routes
                each task to the best model inside one shared conversation.
              </p>

              <p className="text-primary font-semibold text-lg mb-6">
                You used to pay for this entire stack. Now you just need Syntra AI.
              </p>

              <div className="space-y-3">
                <BenefitRow icon={<Sparkles className="w-4 h-4" />} text="One subscription, multiple frontier models" />
                <BenefitRow icon={<Brain className="w-4 h-4" />} text="Unified context and memory across every task" />
                <BenefitRow icon={<Lock className="w-4 h-4" />} text="Encrypted, private workspace" />
                <BenefitRow
                  icon={<Zap className="w-4 h-4" />}
                  text="Automatic routing to the right model for planning, frontend, backend, tests, debugging, and research"
                />
              </div>

              <a
                href="#"
                className="inline-flex items-center gap-2 mt-6 bg-primary text-primary-foreground px-6 py-3 rounded-lg font-medium hover:bg-primary/90 transition-colors"
              >
                Try Syntra Free
                <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>

        <div className={`hidden lg:flex justify-center -mt-[280px] mb-[200px] pointer-events-none transition-all duration-1000 delay-700 ${isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-50'
          }`}>
          <div className="flex items-center gap-2 text-muted-foreground">
            <div className="w-8 h-0.5 bg-border animate-pulse" />
            <ArrowRight className="w-6 h-6 text-primary animate-bounce" style={{ animationDuration: '2s' }} />
            <div className="w-8 h-0.5 bg-border animate-pulse" />
          </div>
        </div>
      </div>
    </section>
  )
}

function StackRow({
  role,
  model,
  iconSrc,
  iconInvert = false,
}: { role: string; model: string; iconSrc: string; iconInvert?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 px-3 bg-muted/30 rounded-lg hover:bg-muted/50 transition-all duration-300 hover:scale-[1.02] group">
      <span className="text-sm text-foreground font-medium">{role}</span>
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground group-hover:text-primary transition-colors">→</span>
        <div className="flex items-center gap-2 bg-muted/50 px-3 py-1 rounded-full group-hover:bg-muted/70 transition-all">
          <div className="w-5 h-5 rounded-full overflow-hidden flex items-center justify-center bg-white group-hover:scale-110 transition-transform">
            <Image
              src={iconSrc || "/placeholder.svg"}
              alt={model}
              width={18}
              height={18}
              className={iconInvert ? "invert" : ""}
            />
          </div>
          <span className="text-xs text-foreground">{model}</span>
        </div>
      </div>
    </div>
  )
}

function BenefitRow({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-start gap-3 hover:translate-x-1 transition-transform duration-300 group">
      <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-primary flex-shrink-0 mt-0.5 group-hover:bg-primary/30 group-hover:scale-110 transition-all duration-300">
        {icon}
      </div>
      <span className="text-sm text-foreground group-hover:text-primary transition-colors">{text}</span>
    </div>
  )
}
