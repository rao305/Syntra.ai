'use client'

import { useAuth } from '@/components/auth/auth-provider'
import { CollaborationModeSection } from "@/components/collaboration-mode-section"
import { ComparisonSection } from "@/components/comparison-section"
import { FAQSection } from "@/components/faq-section"
import { FeaturesSection } from "@/components/features-section"
import { Footer } from "@/components/footer"
import { Header } from "@/components/header"
import { HeroSection } from "@/components/hero-section"
import { ModelLogos } from "@/components/model-logos"
import { PricingSection } from "@/components/pricing-section"
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
    <main className="min-h-screen bg-background relative overflow-x-hidden">
      {/* Floating particles background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-primary/20 rounded-full animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${10 + Math.random() * 10}s`,
            }}
          />
        ))}
      </div>

      <style jsx>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0) translateX(0);
            opacity: 0.2;
          }
          25% {
            transform: translateY(-20px) translateX(10px);
            opacity: 0.4;
          }
          50% {
            transform: translateY(-40px) translateX(-10px);
            opacity: 0.6;
          }
          75% {
            transform: translateY(-20px) translateX(5px);
            opacity: 0.4;
          }
        }
        .animate-float {
          animation: float linear infinite;
        }
      `}</style>

      <Header />
      <HeroSection />
      <ModelLogos />
      <WorkspaceSection />
      <FeaturesSection />
      <CollaborationModeSection />
      <ComparisonSection />
      <PricingSection />
      <FAQSection />
      <Footer />
    </main>
  )
}
