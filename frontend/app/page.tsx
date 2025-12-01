import { Header } from "@/components/header"
import { HeroSection } from "@/components/hero-section"
import { ModelLogos } from "@/components/model-logos"
import { WorkspaceSection } from "@/components/workspace-section"
import { FeaturesSection } from "@/components/features-section"
import { UseCasesSection } from "@/components/use-cases-section"
import { ComparisonSection } from "@/components/comparison-section"
import { PricingSection } from "@/components/pricing-section"
import { FAQSection } from "@/components/faq-section"
import { Footer } from "@/components/footer"

export default function Home() {
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
