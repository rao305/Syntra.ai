'use client'

import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <SignIn
        appearance={{
          elements: {
            rootBox: 'mx-auto',
            card: 'bg-card border border-border shadow-lg rounded-lg',
          },
        }}
        fallbackRedirectUrl="/auth/callback"
        forceRedirectUrl="/auth/callback"
      />
    </div>
  )
}
