'use client'

import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

interface DifferentiatorCardProps {
  icon: LucideIcon
  title: string
  description: string
  delay?: number
}

export function DifferentiatorCard({
  icon: Icon,
  title,
  description,
  delay = 0,
}: DifferentiatorCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.5, delay, ease: 'easeOut' }}
    >
      <Card className="border-white/5 bg-zinc-900/40 backdrop-blur-sm hover:bg-zinc-900/60 transition-all hover:-translate-y-1 h-full">
        <CardContent className="p-6">
          <div className="w-12 h-12 rounded-lg bg-emerald-500/20 border-2 border-emerald-500/30 flex items-center justify-center mb-4">
            <Icon className="w-6 h-6 text-emerald-400" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-3">{title}</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
        </CardContent>
      </Card>
    </motion.div>
  )
}

