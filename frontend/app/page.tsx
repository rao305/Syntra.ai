import { redirect } from 'next/navigation'

export default function Home() {
  // Redirect to conversations page (main workspace)
  redirect('/conversations')
}
