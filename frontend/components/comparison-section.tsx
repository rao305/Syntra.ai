"use client"

import { AnimatePresence, motion, useInView } from "framer-motion"
import { ArrowRight, Brain, Cpu, GitBranch, Layers, Network, Sparkles, Zap } from "lucide-react"
import { useEffect, useRef, useState } from "react"

const uniqueFeatures = [
  {
    icon: Network,
    title: "Multi-Agent Collaboration",
    description: "Intelligent AI agents work together in parallel, each specializing in different aspects of your query",
    highlight: "5+ specialized agents",
    color: "emerald",
  },
  {
    icon: Zap,
    title: "Parallel Processing",
    description: "Multiple AI models execute simultaneously, dramatically reducing response time while improving quality",
    highlight: "3-5x faster",
    color: "blue",
  },
  {
    icon: Brain,
    title: "Dynamic AI Orchestration",
    description: "Intelligent routing automatically selects the best model for each task based on query complexity and requirements",
    highlight: "Adaptive routing",
    color: "purple",
  },
  {
    icon: Layers,
    title: "6-Stage Collaboration Pipeline",
    description: "Structured workflow: Analysis → Research → Creation → Critique → Synthesis → Verification",
    highlight: "Enterprise-grade",
    color: "amber",
  },
  {
    icon: GitBranch,
    title: "Cross-Model Memory Sharing",
    description: "All AI agents share context and insights, creating a unified knowledge base that improves over time",
    highlight: "Shared intelligence",
    color: "cyan",
  },
  {
    icon: Cpu,
    title: "Intelligent Query Routing",
    description: "Automatically determines the optimal collaboration strategy based on your query's intent and complexity",
    highlight: "Auto-optimized",
    color: "rose",
  },
]

export function ComparisonSection() {
  const [activeIndex, setActiveIndex] = useState(0)
  const [mounted, setMounted] = useState(false)
  const headerRef = useRef(null)
  const flowRef = useRef(null)
  const calloutRef = useRef(null)
  const headerInView = useInView(headerRef, { once: true, margin: "-100px" })
  const flowInView = useInView(flowRef, { once: true, margin: "-100px" })
  const calloutInView = useInView(calloutRef, { once: true, margin: "-100px" })

  useEffect(() => {
    setMounted(true)
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % uniqueFeatures.length)
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.95 },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 12,
      },
    },
  }

  const flowItemVariants = {
    hidden: { opacity: 0, scale: 0, rotate: -180 },
    visible: (index: number) => ({
      opacity: 1,
      scale: 1,
      rotate: 0,
      transition: {
        delay: index * 0.15,
        type: "spring",
        stiffness: 200,
        damping: 15,
      },
    }),
  }

  return (
    <section className="py-20 px-6 relative overflow-hidden">
      {/* Animated background particles */}
      {mounted && (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {[...Array(20)].map((_, i) => {
            const initialX = typeof window !== "undefined" ? Math.random() * window.innerWidth : Math.random() * 1200
            const initialY = typeof window !== "undefined" ? Math.random() * window.innerHeight : Math.random() * 800
            const targetY = typeof window !== "undefined" ? Math.random() * window.innerHeight : Math.random() * 800

            return (
              <motion.div
                key={i}
                className="absolute w-1 h-1 bg-emerald-400/20 rounded-full"
                initial={{
                  x: initialX,
                  y: initialY,
                  opacity: 0,
                }}
                animate={{
                  y: [initialY, targetY],
                  opacity: [0, 0.5, 0],
                  scale: [1, 1.5, 1],
                }}
                transition={{
                  duration: Math.random() * 3 + 2,
                  repeat: Infinity,
                  delay: Math.random() * 2,
                  ease: "easeInOut",
                }}
              />
            )
          })}
        </div>
      )}

      <div className="max-w-6xl mx-auto relative z-10">
        <motion.div
          ref={headerRef}
          initial="hidden"
          animate={headerInView ? "visible" : "hidden"}
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: {
                staggerChildren: 0.2,
              },
            },
          }}
          className="text-center mb-16"
        >
          <motion.div
            variants={{
              hidden: { opacity: 0, y: -20, scale: 0.9 },
              visible: {
                opacity: 1,
                y: 0,
                scale: 1,
                transition: {
                  type: "spring",
                  stiffness: 200,
                  damping: 15,
                },
              },
            }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full mb-6"
          >
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            >
              <Sparkles className="w-4 h-4 text-emerald-400" />
            </motion.div>
            <span className="text-sm font-semibold text-emerald-300">SYNTRA EXCLUSIVE</span>
          </motion.div>
          <motion.h2
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: {
                opacity: 1,
                y: 0,
                transition: {
                  type: "spring",
                  stiffness: 100,
                  damping: 12,
                },
              },
            }}
            className="text-3xl md:text-4xl lg:text-5xl font-bold text-foreground mb-4"
          >
            Beyond Single AI: Multi-Agent Intelligence
          </motion.h2>
          <motion.p
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: {
                opacity: 1,
                y: 0,
                transition: {
                  delay: 0.2,
                  type: "spring",
                  stiffness: 100,
                  damping: 12,
                },
              },
            }}
            className="text-lg text-muted-foreground max-w-2xl mx-auto"
          >
            While others use a single AI model, Syntra orchestrates multiple specialized agents working in parallel to deliver superior results
          </motion.p>
        </motion.div>

        {/* Feature Grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12"
        >
          {uniqueFeatures.map((feature, index) => {
            const Icon = feature.icon
            const isActive = index === activeIndex
            const colorClasses = {
              emerald: {
                card: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
                icon: "text-emerald-400",
              },
              blue: {
                card: "bg-blue-500/10 border-blue-500/30 text-blue-300",
                icon: "text-blue-400",
              },
              purple: {
                card: "bg-purple-500/10 border-purple-500/30 text-purple-300",
                icon: "text-purple-400",
              },
              amber: {
                card: "bg-amber-500/10 border-amber-500/30 text-amber-300",
                icon: "text-amber-400",
              },
              cyan: {
                card: "bg-cyan-500/10 border-cyan-500/30 text-cyan-300",
                icon: "text-cyan-400",
              },
              rose: {
                card: "bg-rose-500/10 border-rose-500/30 text-rose-300",
                icon: "text-rose-400",
              },
            }
            const colors = colorClasses[feature.color as keyof typeof colorClasses]

            return (
              <motion.div
                key={index}
                variants={itemVariants}
                className={`group relative p-6 rounded-xl border-2 cursor-pointer overflow-hidden ${isActive
                  ? `${colors.card} shadow-2xl`
                  : "bg-background/50 border-border hover:border-primary/30 hover:bg-background/80"
                  }`}
                onMouseEnter={() => setActiveIndex(index)}
                whileHover={{ scale: 1.02, y: -5 }}
                animate={{
                  scale: isActive ? 1.05 : 1,
                  borderColor: isActive ? undefined : undefined,
                }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
              >
                {/* Animated background gradient */}
                <motion.div
                  className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{
                    background: `radial-gradient(circle at ${Math.random() * 100}% ${Math.random() * 100}%, ${colors.card.split(' ')[0]}, transparent 70%)`,
                  }}
                />
                <div className="relative z-10 flex items-start gap-4">
                  <motion.div
                    className={`p-3 rounded-lg ${isActive ? "bg-background/20" : "bg-muted/50 group-hover:bg-muted"}`}
                    animate={{
                      scale: isActive ? 1.1 : 1,
                      rotate: isActive ? [0, 5, -5, 0] : 0,
                    }}
                    transition={{
                      scale: { type: "spring", stiffness: 300, damping: 20 },
                      rotate: { duration: 0.5, repeat: isActive ? Infinity : 0, repeatDelay: 2 },
                    }}
                  >
                    <motion.div
                      animate={{
                        rotate: isActive ? [0, 360] : 0,
                      }}
                      transition={{
                        duration: 2,
                        repeat: isActive ? Infinity : 0,
                        ease: "linear",
                      }}
                    >
                      <Icon className={`w-6 h-6 ${isActive ? colors.icon : "text-muted-foreground"}`} />
                    </motion.div>
                  </motion.div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-bold text-foreground text-lg">{feature.title}</h3>
                      <AnimatePresence>
                        {isActive && (
                          <motion.div
                            initial={{ scale: 0, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0, opacity: 0 }}
                            className="w-2 h-2 rounded-full bg-emerald-400"
                          >
                            <motion.div
                              className="w-2 h-2 rounded-full bg-emerald-400"
                              animate={{
                                scale: [1, 2, 1],
                                opacity: [1, 0, 1],
                              }}
                              transition={{
                                duration: 1.5,
                                repeat: Infinity,
                                ease: "easeInOut",
                              }}
                            />
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                    <motion.p
                      className="text-sm text-muted-foreground mb-3 leading-relaxed"
                      animate={{
                        color: isActive ? colors.card.split(' ')[2] : undefined,
                      }}
                      transition={{ duration: 0.3 }}
                    >
                      {feature.description}
                    </motion.p>
                    <motion.div
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-semibold ${isActive ? "bg-background/30 text-foreground" : "bg-muted text-muted-foreground"
                        }`}
                      whileHover={{ scale: 1.05 }}
                      animate={{
                        scale: isActive ? 1.05 : 1,
                      }}
                    >
                      <motion.div
                        animate={{
                          rotate: isActive ? [0, 360] : 0,
                        }}
                        transition={{
                          duration: 1,
                          repeat: isActive ? Infinity : 0,
                          ease: "linear",
                        }}
                      >
                        <Zap className="w-3 h-3" />
                      </motion.div>
                      {feature.highlight}
                    </motion.div>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </motion.div>

        {/* Visual Flow Diagram */}
        <motion.div
          ref={flowRef}
          initial="hidden"
          animate={flowInView ? "visible" : "hidden"}
          className="mt-16 p-8 rounded-2xl bg-gradient-to-br from-emerald-500/10 via-blue-500/10 to-purple-500/10 border border-emerald-500/20 relative overflow-hidden"
        >
          {/* Animated gradient background */}
          <motion.div
            className="absolute inset-0 opacity-30"
            animate={{
              background: [
                "radial-gradient(circle at 0% 50%, rgba(16, 185, 129, 0.1), transparent 50%)",
                "radial-gradient(circle at 100% 50%, rgba(59, 130, 246, 0.1), transparent 50%)",
                "radial-gradient(circle at 50% 0%, rgba(168, 85, 247, 0.1), transparent 50%)",
                "radial-gradient(circle at 0% 50%, rgba(16, 185, 129, 0.1), transparent 50%)",
              ],
            }}
            transition={{
              duration: 10,
              repeat: Infinity,
              ease: "linear",
            }}
          />
          <div className="relative z-10">
            <motion.h3
              initial={{ opacity: 0, y: -20 }}
              animate={flowInView ? { opacity: 1, y: 0 } : { opacity: 0, y: -20 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 100 }}
              className="text-2xl font-bold text-foreground text-center mb-8"
            >
              How Multi-Agent Collaboration Works
            </motion.h3>
            <div className="flex flex-wrap items-center justify-center gap-4 md:gap-6">
              {["Query", "Analysis", "Research", "Creation", "Critique", "Synthesis", "Response"].map(
                (stage, index) => (
                  <div key={index} className="flex items-center gap-4 md:gap-6">
                    <motion.div
                      custom={index}
                      variants={flowItemVariants}
                      className="flex flex-col items-center gap-2"
                    >
                      <motion.div
                        className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm ${index === 0 || index === 6
                          ? "bg-emerald-500/30 text-emerald-300 border-2 border-emerald-400/50"
                          : "bg-blue-500/20 text-blue-300 border-2 border-blue-400/30"
                          }`}
                        animate={{
                          scale: flowInView ? [1, 1.1, 1] : 1,
                          boxShadow: flowInView
                            ? [
                              "0 0 0px rgba(16, 185, 129, 0)",
                              "0 0 20px rgba(16, 185, 129, 0.5)",
                              "0 0 0px rgba(16, 185, 129, 0)",
                            ]
                            : undefined,
                        }}
                        transition={{
                          delay: index * 0.15 + 0.5,
                          duration: 1,
                          repeat: Infinity,
                          repeatDelay: 3,
                        }}
                      >
                        {index + 1}
                      </motion.div>
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={flowInView ? { opacity: 1 } : { opacity: 0 }}
                        transition={{ delay: index * 0.15 + 0.3 }}
                        className="text-xs font-medium text-muted-foreground text-center max-w-[80px]"
                      >
                        {stage}
                      </motion.span>
                    </motion.div>
                    {index < 6 && (
                      <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={flowInView ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
                        transition={{ delay: index * 0.15 + 0.4 }}
                        className="hidden md:block"
                      >
                        <motion.div
                          animate={{
                            x: [0, 5, 0],
                          }}
                          transition={{
                            duration: 1.5,
                            repeat: Infinity,
                            delay: index * 0.2,
                            ease: "easeInOut",
                          }}
                        >
                          <ArrowRight className="w-5 h-5 text-muted-foreground" />
                        </motion.div>
                      </motion.div>
                    )}
                  </div>
                )
              )}
            </div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={flowInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
              transition={{ delay: 1.2, type: "spring", stiffness: 100 }}
              className="mt-8 text-center"
            >
              <p className="text-sm text-muted-foreground">
                <motion.span
                  className="font-semibold text-emerald-300"
                  animate={{
                    textShadow: [
                      "0 0 0px rgba(16, 185, 129, 0)",
                      "0 0 10px rgba(16, 185, 129, 0.5)",
                      "0 0 0px rgba(16, 185, 129, 0)",
                    ],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                >
                  Multiple AI models
                </motion.span>{" "}
                execute stages{" "}
                <motion.span
                  className="font-semibold text-blue-300"
                  animate={{
                    textShadow: [
                      "0 0 0px rgba(59, 130, 246, 0)",
                      "0 0 10px rgba(59, 130, 246, 0.5)",
                      "0 0 0px rgba(59, 130, 246, 0)",
                    ],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: 1,
                    ease: "easeInOut",
                  }}
                >
                  in parallel
                </motion.span>{" "}
                for faster, higher-quality results
              </p>
            </motion.div>
          </div>
        </motion.div>

        {/* Comparison Callout */}
        <motion.div
          ref={calloutRef}
          initial="hidden"
          animate={calloutInView ? "visible" : "hidden"}
          variants={{
            hidden: { opacity: 0, y: 30 },
            visible: {
              opacity: 1,
              y: 0,
              transition: {
                type: "spring",
                stiffness: 100,
                damping: 15,
                staggerChildren: 0.1,
              },
            },
          }}
          className="mt-12 p-6 rounded-xl bg-background/50 border border-border relative overflow-hidden"
        >
          {/* Animated border glow */}
          <motion.div
            className="absolute inset-0 rounded-xl"
            style={{
              background: "linear-gradient(90deg, transparent, rgba(16, 185, 129, 0.1), transparent)",
            }}
            animate={{
              x: ["-100%", "200%"],
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              ease: "linear",
            }}
          />
          <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-4">
            <motion.div
              variants={{
                hidden: { opacity: 0, x: -30 },
                visible: {
                  opacity: 1,
                  x: 0,
                  transition: { type: "spring", stiffness: 100 },
                },
              }}
            >
              <h4 className="font-bold text-foreground mb-2">Traditional AI Assistants</h4>
              <p className="text-sm text-muted-foreground">
                Single model, sequential processing, limited capabilities
              </p>
            </motion.div>
            <motion.div
              variants={{
                hidden: { opacity: 0, scale: 0 },
                visible: {
                  opacity: 1,
                  scale: 1,
                  transition: { delay: 0.2, type: "spring", stiffness: 200 },
                },
              }}
              animate={{
                x: [0, 10, 0],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            >
              <ArrowRight className="w-6 h-6 text-muted-foreground rotate-90 md:rotate-0" />
            </motion.div>
            <motion.div
              variants={{
                hidden: { opacity: 0, x: 30 },
                visible: {
                  opacity: 1,
                  x: 0,
                  transition: { delay: 0.3, type: "spring", stiffness: 100 },
                },
              }}
              className="text-center md:text-right"
            >
              <motion.h4
                className="font-bold text-emerald-300 mb-2"
                animate={{
                  textShadow: [
                    "0 0 0px rgba(16, 185, 129, 0)",
                    "0 0 15px rgba(16, 185, 129, 0.6)",
                    "0 0 0px rgba(16, 185, 129, 0)",
                  ],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              >
                Syntra's Multi-Agent System
              </motion.h4>
              <p className="text-sm text-muted-foreground">
                Multiple specialized agents, parallel execution, superior intelligence
              </p>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
