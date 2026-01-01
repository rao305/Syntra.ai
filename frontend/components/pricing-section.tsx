"use client"

import type React from "react"

import { useState } from "react"
import { Check, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"

export function PricingSection() {
  const [isAnnual, setIsAnnual] = useState(false)

  return (
    <section id="pricing" className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-foreground mb-4">
            Simple pricing for everyone
          </h2>
          <p className="text-muted-foreground">Start free, upgrade when you're ready. No hidden fees, no surprises.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {/* Pro Plan */}
          <div className="bg-zinc-800/80 rounded-2xl border border-zinc-700/50 p-8">
            <h3 className="text-xl font-semibold text-foreground mb-4">Pro</h3>
            <div className="flex items-baseline gap-1 mb-2">
              <span className="text-4xl font-bold text-foreground">$15</span>
              <span className="text-muted-foreground">/mo</span>
            </div>
            <p className="text-sm text-muted-foreground mb-4">Billed monthly</p>

            <div className="flex items-center gap-2 mb-6">
              <span className="text-sm text-muted-foreground">Save 17% with annual billing</span>
              <Switch checked={isAnnual} onCheckedChange={setIsAnnual} />
            </div>

            <Button className="w-full bg-white text-black hover:bg-gray-100 mb-4">Get Pro Now</Button>

            <p className="text-xs text-muted-foreground text-center mb-6">Loved by 26,000+ users</p>

            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">Everything in Hobby, plus</p>
              <FeatureItem>Access to ChatGPT, Claude, Gemini, Kimi K2, and Llama in one workspace</FeatureItem>
              <FeatureItem>Unified memory across conversations and models</FeatureItem>
              <FeatureItem>Encrypted chat and file storage</FeatureItem>
            </div>
          </div>

          {/* Founding User Plan */}
          <div
            className="rounded-2xl p-8 relative overflow-hidden"
            style={{ background: "linear-gradient(180deg, #7f1d1d 0%, #450a0a 100%)" }}
          >
            <h3 className="text-xl font-semibold text-white mb-4">Founding User</h3>
            <div className="flex items-baseline gap-1 mb-2">
              <span className="text-4xl font-bold text-white">$500</span>
              <span className="text-gray-300">one-time</span>
            </div>
            <p className="text-sm text-gray-300 mb-2">Lifetime Pro access</p>
            <p className="text-xs text-gray-400 text-center mb-4">Only 100 founding member spots available</p>

            <Button className="w-full bg-white text-primary hover:bg-gray-100 mb-4">Claim Your Spot</Button>

            <div className="flex items-center justify-center gap-2 mb-6 text-sm text-gray-300">
              <Clock className="w-4 h-4" />
              <span>Offer ends in 12d 23h 3m</span>
            </div>

            <p className="text-sm text-gray-300 mb-4">Become a founding member and get:</p>
            <div className="space-y-3">
              <FeatureItemWhite>All Pro features forever</FeatureItemWhite>
              <FeatureItemWhite>Lifetime platform access</FeatureItemWhite>
              <FeatureItemWhite>Priority support</FeatureItemWhite>
              <FeatureItemWhite>Early access to new features and models</FeatureItemWhite>
            </div>
          </div>

          {/* Enterprise Plan */}
          <div className="bg-zinc-800/80 rounded-2xl border border-zinc-700/50 p-8">
            <h3 className="text-xl font-semibold text-foreground mb-4">Enterprise</h3>
            <div className="mb-2">
              <span className="text-3xl font-bold text-foreground">Custom Pricing</span>
            </div>
            <p className="text-sm text-muted-foreground mb-6">Billed annually</p>

            <Button
              variant="outline"
              className="w-full border-border bg-secondary text-foreground hover:bg-secondary/80 mb-6"
            >
              Contact Sales
            </Button>

            <div className="space-y-3">
              <FeatureItem>Everything in Pro plan</FeatureItem>
              <FeatureItem>Optional private cloud deployment</FeatureItem>
              <FeatureItem>Custom model routing and usage policies</FeatureItem>
              <FeatureItem>Single sign-on (SSO) and advanced access controls</FeatureItem>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function FeatureItem({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <Check className="w-5 h-5 text-accent shrink-0 mt-0.5" />
      <span className="text-sm text-foreground">{children}</span>
    </div>
  )
}

function FeatureItemWhite({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <Check className="w-5 h-5 text-white shrink-0 mt-0.5" />
      <span className="text-sm text-white">{children}</span>
    </div>
  )
}
