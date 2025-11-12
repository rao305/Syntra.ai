'use client'

import * as React from 'react'
import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Check, ArrowRight } from 'lucide-react'
import Link from 'next/link'

const plans = [
  {
    name: 'Starter',
    price: { monthly: 0, annual: 0 },
    description: 'Perfect for individuals and small teams getting started',
    features: [
      '1 LLM Provider',
      '1 Team Seat',
      'Community Support',
      'Basic Routing',
      'Up to 1,000 requests/month',
    ],
    cta: 'Get Started',
    popular: false,
    color: 'border-border',
  },
  {
    name: 'Pro',
    price: { monthly: 49, annual: 490 },
    description: 'For growing teams that need more power and flexibility',
    features: [
      '4+ LLM Providers',
      '5 Team Seats',
      'Priority Support',
      'Advanced Routing',
      'Unlimited Requests',
      'Usage Analytics',
      'Custom Policies',
    ],
    cta: 'Start Free Trial',
    popular: true,
    color: 'border-emerald-500',
  },
  {
    name: 'Enterprise',
    price: { monthly: null, annual: null },
    description: 'Custom solutions for large organizations',
    features: [
      'Unlimited Providers',
      'Unlimited Team Seats',
      'SLA & Dedicated Support',
      'SSO & Advanced Security',
      'Custom Integrations',
      'On-premise Options',
      'Dedicated Account Manager',
    ],
    cta: 'Contact Sales',
    popular: false,
    color: 'border-border',
  },
]

export default function PricingPage() {
  const [isAnnual, setIsAnnual] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="border-b border-border bg-zinc-900/60 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center space-y-6">
            <h1 className="text-5xl font-bold text-foreground tracking-tight">
              Simple, transparent pricing
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Choose the plan that fits your team. Upgrade or downgrade at any time.
            </p>

            {/* Billing Toggle */}
            <div className="flex items-center justify-center gap-4 pt-4">
              <Label htmlFor="billing-toggle" className="text-sm text-muted-foreground">
                Monthly
              </Label>
              <Switch
                id="billing-toggle"
                checked={isAnnual}
                onCheckedChange={setIsAnnual}
                className="data-[state=checked]:bg-emerald-600"
              />
              <Label htmlFor="billing-toggle" className="text-sm text-muted-foreground">
                Annual
                <span className="ml-2 text-xs text-emerald-400">(Save 17%)</span>
              </Label>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {plans.map((plan) => (
              <Card
                key={plan.name}
                className={`relative border-2 ${plan.color} ${
                  plan.popular
                    ? 'bg-zinc-900/60 backdrop-blur-sm scale-105'
                    : 'bg-zinc-900/40 backdrop-blur-sm'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="bg-emerald-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                      Most Popular
                    </span>
                  </div>
                )}
                <CardHeader>
                  <CardTitle className="text-2xl">{plan.name}</CardTitle>
                  <CardDescription className="mt-2">{plan.description}</CardDescription>
                  <div className="mt-6">
                    {plan.price.monthly === null ? (
                      <div className="text-3xl font-bold text-foreground">Custom</div>
                    ) : (
                      <div className="flex items-baseline gap-2">
                        <span className="text-4xl font-bold text-foreground">
                          ${isAnnual ? plan.price.annual : plan.price.monthly}
                        </span>
                        <span className="text-muted-foreground">
                          /{isAnnual ? 'year' : 'month'}
                        </span>
                      </div>
                    )}
                    {plan.price.monthly === 0 && (
                      <p className="text-sm text-muted-foreground mt-2">Forever free</p>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  <ul className="space-y-3">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="flex items-start gap-3">
                        <Check className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-muted-foreground">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Link href={plan.name === 'Enterprise' ? '/contact' : '/'} className="block">
                    <Button
                      className={`w-full ${
                        plan.popular
                          ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                          : 'bg-background hover:bg-accent'
                      }`}
                      variant={plan.popular ? 'default' : 'outline'}
                    >
                      {plan.cta}
                      {plan.name !== 'Enterprise' && (
                        <ArrowRight className="ml-2 w-4 h-4" />
                      )}
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-16 border-t border-border">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-foreground text-center mb-12">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-foreground">
                Can I change plans later?
              </h3>
              <p className="text-muted-foreground">
                Yes, you can upgrade or downgrade your plan at any time. Changes take effect
                immediately, and we'll prorate any charges.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-foreground">
                What payment methods do you accept?
              </h3>
              <p className="text-muted-foreground">
                We accept all major credit cards. Enterprise customers can also pay via invoice.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-foreground">
                Is there a free trial?
              </h3>
              <p className="text-muted-foreground">
                Yes, Pro plans include a 14-day free trial. No credit card required.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-foreground">
                How does usage-based pricing work?
              </h3>
              <p className="text-muted-foreground">
                You only pay for what you use. We track tokens, requests, and API calls, and bill
                you monthly based on actual usage.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 border-t border-border bg-zinc-900/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-foreground mb-4">
            Still have questions?
          </h2>
          <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
            Our team is here to help you choose the right plan for your needs.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/">
              <Button size="lg" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                Start Free Trial
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
            <Link href="/contact">
              <Button size="lg" variant="outline">
                Contact Sales
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

