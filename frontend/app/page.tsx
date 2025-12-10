'use client'

import { useAuth } from '@/components/auth/auth-provider'
import { ComparisonSection } from "@/components/comparison-section"
import { FAQSection } from "@/components/faq-section"
import { FeaturesSection } from "@/components/features-section"
import { Footer } from "@/components/footer"
import { Header } from "@/components/header"
import { HeroSection } from "@/components/hero-section"
import { ModelLogos } from "@/components/model-logos"
import { PricingSection } from "@/components/pricing-section"
import { UseCasesSection } from "@/components/use-cases-section"
import { WorkspaceSection } from "@/components/workspace-section"
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function Home() {
  const { user, accessToken, loading } = useAuth()
  const router = useRouter()

  // Redirect authenticated users to conversations ONLY if backend session is ready
  useEffect(() => {
    if (!loading && user && accessToken) {
      router.push('/conversations')
    }
  }, [loading, user, accessToken, router])

  // Show loading state while checking auth
  if (loading) {
    return (
      <main className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </main>
    )
  }

  // If signed in (backend ready), show loading while redirecting
  if (user && accessToken) {
    return (
      <main className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </main>
    )
  }

  // Show homepage for unauthenticated users
  return (
    <main className="min-h-screen bg-background">
      <Header />
      <HeroSection />
      <ModelLogos />
      <WorkspaceSection />
      <FeaturesSection />
      <UseCasesSection />
      <ComparisonSection />
      <PricingSection />
      <FAQSection />
      <Footer />
    </main>
  )
}
