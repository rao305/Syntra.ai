'use client'

import * as React from 'react'
import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Check, ArrowRight, X, Sparkles, Brain, Code2, Image as ImageIcon } from 'lucide-react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'

const plans = [
  {
    name: 'Starter',
    price: { monthly: 0, annual: 0 },
    description: 'Perfect for individuals and small teams getting started',
    features: [
      'Multi-Model Shared Context (Only Syntra)',
      'Zero-Context-Switching Chats',
      'Automatic Task-Based Model Routing',
      'Up to 2 LLM Providers',
      '1 Team Seat',
      'Up to 5,000 requests/month',
      'Community Support',
      'Basic Observability',
    ],
    cta: 'Get Started',
    popular: false,
    highlight: false,
  },
  {
    name: 'Pro',
    price: { monthly: 99, annual: 990 },
    description: 'For growing teams that need multi-model power',
    features: [
      'Multi-Model Shared Context (Only Syntra)',
      'Zero-Context-Switching Chats',
      'Automatic Task-Based Model Routing',
      'Model Collaboration (Ensembles)',
      'Unlimited Provider Switching',
      'Unified Token Monitoring',
      'Unified Audit Logs',
      'Bring Your Own Keys',
      'Local + Cloud Models in One Thread',
      'Unlimited Requests',
      '5 Team Seats',
      'Priority Support',
      'Advanced Routing Policies',
    ],
    cta: 'Start Free Trial',
    popular: true,
    highlight: true,
  },
  {
    name: 'Enterprise',
    price: { monthly: null, annual: null },
    description: 'Custom solutions for large organizations',
    features: [
      'Everything in Pro',
      'Unlimited Team Seats',
      'SLA & Dedicated Support',
      'SSO & Advanced Security',
      'Custom Integrations',
      'On-premise Options',
      'Dedicated Account Manager',
      'Custom SLA Guarantees',
      'White-glove Onboarding',
    ],
    cta: 'Contact Sales',
    popular: false,
    highlight: false,
  },
]

const comparisonData = [
  {
    category: 'Setup',
    diy: '5 model accounts',
    dac: 'One assistant',
    icon: Sparkles,
  },
  {
    category: 'Billing',
    diy: '5 billing dashboards',
    dac: 'One unified billing',
    icon: Sparkles,
  },
  {
    category: 'Context',
    diy: 'No shared context',
    dac: 'One context window',
    icon: Sparkles,
  },
  {
    category: 'API',
    diy: '5 different APIs',
    dac: 'One API',
    icon: Sparkles,
  },
  {
    category: 'Routing',
    diy: 'Manual routing logic',
    dac: 'Automatic routing',
    icon: Sparkles,
  },
  {
    category: 'Features',
    diy: 'No fallbacks',
    dac: 'Ensembles & fallbacks',
    icon: Sparkles,
  },
  {
    category: 'Reliability',
    diy: 'No observability',
    dac: '100% uptime SLA',
    icon: Sparkles,
  },
]

const modelLogos = [
  { name: 'OpenAI', icon: Code2, color: 'text-green-400' },
  { name: 'Claude', icon: Brain, color: 'text-orange-400' },
  { name: 'Gemini', icon: ImageIcon, color: 'text-blue-400' },
]

export default function PricingPage() {
  const [isAnnual, setIsAnnual] = useState(true)
  const [logoAnimation, setLogoAnimation] = useState(true)

  React.useEffect(() => {
    const timer = setTimeout(() => setLogoAnimation(false), 3000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="min-h-screen bg-[#020409]">
      {/* Hero Section */}
      <section className="relative border-b border-white/10 bg-gradient-to-b from-[#020409] via-[#050810] to-[#020409] overflow-hidden py-24 md:py-32">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(34,197,94,0.1),transparent_50%)]" />

        {/* Animated Model Logos Collapsing */}
        <div className="absolute inset-0 flex items-center justify-center">
          <AnimatePresence mode="wait">
            {logoAnimation ? (
              <motion.div
                key="multiple"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="flex items-center gap-8"
              >
                {modelLogos.map((logo, index) => {
                  const Icon = logo.icon
                  return (
                    <motion.div
                      key={logo.name}
                      initial={{ opacity: 0, x: -50, scale: 0.8 }}
                      animate={{ opacity: 1, x: 0, scale: 1 }}
                      transition={{ delay: index * 0.2, duration: 0.5 }}
                      className="w-16 h-16 rounded-xl bg-zinc-900/80 border border-white/10 flex items-center justify-center backdrop-blur-sm"
                    >
                      <Icon className={`w-8 h-8 ${logo.color}`} />
                    </motion.div>
                  )
                })}
                <motion.div
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.8, duration: 0.5 }}
                  className="text-2xl text-muted-foreground mx-4"
                >
                  →
                </motion.div>
              </motion.div>
            ) : (
              <motion.div
                key="dac"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, type: 'spring' }}
                className="w-24 h-24 rounded-2xl bg-gradient-to-br from-emerald-500/30 to-teal-500/30 flex items-center justify-center border-2 border-emerald-500/40 ring-4 ring-emerald-500/20"
              >
                <Sparkles className="w-12 h-12 text-emerald-400" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Content */}
        <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          
            <div className="text-center space-y-6">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-100 tracking-tight">
                Simple Pricing for a
                <br />
                <span className="text-emerald-400">Complex Multi-Model World.</span>
              </h1>
              <p className="text-lg md:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed">
                Syntra replaces multiple LLM accounts, multiple APIs, complex routing logic, context
                syncing, and reliability engineering — all with one subscription.
              </p>

              {/* Billing Toggle */}
              <div className="flex items-center justify-center pt-8">
                <div className="flex items-center gap-4 bg-zinc-900/60 border border-white/10 rounded-full p-1.5">
                  <button
                    onClick={() => setIsAnnual(false)}
                    className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                      !isAnnual
                        ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/20'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Monthly
                  </button>
                  <button
                    onClick={() => setIsAnnual(true)}
                    className={`px-6 py-2 rounded-full text-sm font-medium transition-all relative ${
                      isAnnual
                        ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/20'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Annual
                    <span className="ml-2 text-xs bg-emerald-500/20 px-2 py-0.5 rounded-full">
                      Save 17%
                    </span>
                  </button>
                </div>
              </div>
            </div>
          
        </div>
      </section>

      {/* Metrics Strip */}
      

      {/* Pricing Cards */}
      <section className="py-16 md:py-24 border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {plans.map((plan, index) => (
                <motion.div
                  key={plan.name}
                  variants={item}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: index * 0.1 }}
                >
                  <Card
                    className={`relative border-2 transition-all h-full flex flex-col group ${
                      plan.highlight
                        ? 'border-emerald-500/50 bg-zinc-900/60 backdrop-blur-sm scale-105 shadow-2xl shadow-emerald-500/20'
                        : 'border-white/10 bg-zinc-900/40 backdrop-blur-sm hover:border-emerald-500/30'
                    }`}
                    onMouseEnter={(e) => {
                      if (plan.highlight) {
                        e.currentTarget.style.boxShadow =
                          '0 0 40px rgba(34, 197, 94, 0.3), 0 0 80px rgba(34, 197, 94, 0.1)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (plan.highlight) {
                        e.currentTarget.style.boxShadow =
                          '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 0 40px rgba(34, 197, 94, 0.2)'
                      }
                    }}
                  >
                    {plan.highlight && (
                      <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                        <span className="bg-emerald-600 text-white text-xs font-semibold px-4 py-1.5 rounded-full shadow-lg">
                          Most Popular
                        </span>
                      </div>
                    )}
                    <CardHeader className="pb-4">
                      <CardTitle className="text-2xl mb-2">{plan.name}</CardTitle>
                      <CardDescription className="text-sm">{plan.description}</CardDescription>
                      <div className="mt-6">
                        {plan.price.monthly === null ? (
                          <div className="text-3xl font-bold text-foreground">Custom</div>
                        ) : (
                          <div className="flex items-baseline gap-2">
                            <span className="text-4xl font-bold text-foreground">
                              ${isAnnual ? plan.price.annual : plan.price.monthly}
                            </span>
                            <span className="text-muted-foreground text-sm">
                              /{isAnnual ? 'year' : 'month'}
                            </span>
                          </div>
                        )}
                        {plan.price.monthly === 0 && (
                          <p className="text-sm text-muted-foreground mt-2">Forever free</p>
                        )}
                        {plan.price.monthly !== null && plan.price.monthly !== 0 && isAnnual && (
                          <p className="text-xs text-emerald-400 mt-1">
                            ${plan.price.monthly}/month billed annually
                          </p>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6 flex-1 flex flex-col">
                      <ul className="space-y-3 flex-1">
                        {plan.features.map((feature, idx) => (
                          <motion.li
                            key={idx}
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.3, delay: idx * 0.05 }}
                            className="flex items-start gap-3"
                          >
                            <motion.div
                              initial={{ scale: 0 }}
                              whileInView={{ scale: 1 }}
                              viewport={{ once: true }}
                              transition={{ duration: 0.3, delay: idx * 0.05, type: 'spring' }}
                            >
                              <Check className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                            </motion.div>
                            <span className="text-sm text-muted-foreground leading-relaxed">
                              {feature}
                            </span>
                          </motion.li>
                        ))}
                      </ul>
                      <Link
                        href={plan.name === 'Enterprise' ? '/contact' : '/conversations'}
                        className="block mt-auto"
                      >
                        <Button
                          className={`w-full h-11 ${
                            plan.highlight
                              ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-500/20'
                              : 'bg-background hover:bg-accent'
                          }`}
                          variant={plan.highlight ? 'default' : 'outline'}
                        >
                          {plan.cta}
                          {plan.name !== 'Enterprise' && (
                            <ArrowRight className="ml-2 w-4 h-4" />
                          )}
                        </Button>
                      </Link>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          
        </div>
      </section>

      {/* Cost Savings Section */}
      <section className="py-16 md:py-24 border-b border-white/10 bg-zinc-900/20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
                Why Syntra is cheaper than using models directly
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Stop managing multiple accounts, APIs, and routing logic. One platform, one price,
                infinite possibilities.
              </p>
            </div>
          

          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {/* DIY Column */}
            
              <Card className="border-red-500/20 bg-red-500/5 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-xl text-red-400">Building It Yourself</CardTitle>
                  <CardDescription>What you need to manage</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-4">
                    {comparisonData.map((item, index) => {
                      const Icon = item.icon
                      return (
                        <motion.li
                          key={index}
                          initial={{ opacity: 0, x: -50 }}
                          whileInView={{ opacity: 1, x: 0 }}
                          viewport={{ once: true }}
                          transition={{ duration: 0.4, delay: index * 0.1 }}
                          className="flex items-start gap-3"
                        >
                          <X className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-sm font-medium text-foreground mb-1">
                              {item.category}
                            </div>
                            <div className="text-xs text-muted-foreground">{item.diy}</div>
                          </div>
                        </motion.li>
                      )
                    })}
                  </ul>
                </CardContent>
              </Card>
            

            {/* Syntra Column */}
            
              <Card className="border-emerald-500/50 bg-emerald-500/10 backdrop-blur-sm shadow-lg shadow-emerald-500/10">
                <CardHeader>
                  <CardTitle className="text-xl text-emerald-400">Syntra</CardTitle>
                  <CardDescription>One platform, everything included</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-4">
                    {comparisonData.map((item, index) => {
                      const Icon = item.icon
                      return (
                        <motion.li
                          key={index}
                          initial={{ opacity: 0, x: 50 }}
                          whileInView={{ opacity: 1, x: 0 }}
                          viewport={{ once: true }}
                          transition={{ duration: 0.4, delay: index * 0.1 }}
                          className="flex items-start gap-3"
                        >
                          <Check className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-sm font-medium text-foreground mb-1">
                              {item.category}
                            </div>
                            <div className="text-xs text-muted-foreground">{item.dac}</div>
                          </div>
                        </motion.li>
                      )
                    })}
                  </ul>
                </CardContent>
              </Card>
            
          </div>
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
                Start building today.
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Join teams using Syntra to unify their AI infrastructure and build faster.
              </p>
              <div className="flex items-center justify-center gap-4 pt-4">
                <Link href="/conversations">
                  <Button
                    size="lg"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white h-12 px-8"
                  >
                    Get Started Free
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </Link>
                <Link href="/contact">
                  <Button size="lg" variant="outline" className="h-12 px-8">
                    Contact Sales
                  </Button>
                </Link>
              </div>
            </motion.div>
          
        </div>
      </section>
    </div>
  )
}
