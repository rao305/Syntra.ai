import { AuthProvider } from "@/components/auth/auth-provider"
import { ConditionalLayout } from "@/components/conditional-layout"
import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

// Get app URL from environment variable or use default
const appUrl = process.env.NEXT_PUBLIC_APP_URL ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "https://dac.ai")

export const metadata: Metadata = {
  metadataBase: new URL(appUrl),
  title: "Syntra - Intelligent LLM Routing Platform",
  description: "Enterprise AI routing platform. Operate across LLMs with intelligent provider selection, unified context, and enterprise-grade security.",
  keywords: ["AI", "LLM", "routing", "enterprise", "OpenAI", "Anthropic", "Gemini", "API"],
  authors: [{ name: "Syntra Team" }],
  openGraph: {
    title: "Syntra - Intelligent LLM Routing Platform",
    description: "Enterprise AI routing platform. Operate across LLMs with intelligent provider selection, unified context, and enterprise-grade security.",
    type: "website",
    url: appUrl,
    siteName: "Syntra",
    images: [
      {
        url: "/syntra.png",
        width: 180,
        height: 180,
        alt: "Syntra Logo",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Syntra - Intelligent LLM Routing Platform",
    description: "Enterprise AI routing platform with intelligent provider selection and unified context.",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/syntra.png" type="image/png" />
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&family=Google+Sans:wght@400;500&display=swap" rel="stylesheet" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "Syntra",
              applicationCategory: "BusinessApplication",
              operatingSystem: "Web",
              offers: {
                "@type": "Offer",
                price: "0",
                priceCurrency: "USD",
              },
              description:
                "Enterprise AI routing platform for intelligent LLM provider selection",
            }),
          }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col`}
        suppressHydrationWarning
      >
        <AuthProvider>
          <ConditionalLayout>{children}</ConditionalLayout>
        </AuthProvider>
      </body>
    </html>
  )
}
