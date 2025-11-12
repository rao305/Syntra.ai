import { redirect } from 'next/navigation'

export default function ProvidersPageRedirect() {
  // Redirect to main settings page with providers tab
  redirect('/settings?tab=providers')
}
