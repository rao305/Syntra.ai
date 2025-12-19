'use client'

import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

interface FeatureCardProps {
  icon: LucideIcon
  title: string
  description: string
  features: string[]
  color: 'emerald' | 'blue' | 'purple' | 'orange' | 'green' | 'teal'
  delay?: number
}

const colorClasses = {
  emerald: {
    iconBg: 'bg-emerald-500/20',
    iconBorder: 'border-emerald-500/30',
    iconColor: 'text-emerald-400',
    accent: 'text-emerald-400',
  },
  blue: {
    iconBg: 'bg-blue-500/20',
    iconBorder: 'border-blue-500/30',
    iconColor: 'text-blue-400',
    accent: 'text-blue-400',
  },
  purple: {
    iconBg: 'bg-purple-500/20',
    iconBorder: 'border-purple-500/30',
    iconColor: 'text-purple-400',
    accent: 'text-purple-400',
  },
  orange: {
    iconBg: 'bg-orange-500/20',
    iconBorder: 'border-orange-500/30',
    iconColor: 'text-orange-400',
    accent: 'text-orange-400',
  },
  green: {
    iconBg: 'bg-green-500/20',
    iconBorder: 'border-green-500/30',
    iconColor: 'text-green-400',
    accent: 'text-green-400',
  },
  teal: {
    iconBg: 'bg-teal-500/20',
    iconBorder: 'border-teal-500/30',
    iconColor: 'text-teal-400',
    accent: 'text-teal-400',
  },
}

export function FeatureCard({
  icon: Icon,
  title,
  description,
  features,
  color,
  delay = 0,
}: FeatureCardProps) {
  const colors = colorClasses[color]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.5, delay, ease: 'easeOut' }}
    >
      <Card className="border-white/5 bg-zinc-900/40 backdrop-blur-sm hover:bg-zinc-900/60 transition-all hover:-translate-y-1 h-full">
        <CardContent className="p-6">
          <div
            className={`w-12 h-12 rounded-lg ${colors.iconBg} ${colors.iconBorder} border-2 flex items-center justify-center mb-4`}
          >
            <Icon className={`w-6 h-6 ${colors.iconColor}`} />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
          <p className="text-sm text-muted-foreground mb-4">{description}</p>
          <ul className="space-y-2">
            {features.map((feature, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-muted-foreground">
                <span className={colors.accent}>&#8226;</span>
                <span>{feature}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </motion.div>
  )
}



