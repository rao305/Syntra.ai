'use client'

import { useAuth } from '@/components/auth/auth-provider'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function CallbackPage() {
  const { user, accessToken, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading) {
      if (user && accessToken) {
        // Successfully authenticated with backend
        router.push('/conversations')
      } else {
        // Failed to exchange token, go back to sign-in
        router.push('/auth/sign-in?error=auth_failed')
      }
    }
  }, [loading, user, accessToken, router])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
        <p className="text-muted-foreground">Completing authentication...</p>
      </div>
    </div>
  )
}
