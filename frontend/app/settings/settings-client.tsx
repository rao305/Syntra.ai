'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  User,
  Building2,
  Key,
  Route,
  CreditCard,
  Shield,
  BarChart3,
  ArrowRight
} from 'lucide-react'
import Link from 'next/link'
import dynamic from 'next/dynamic'

// Dynamically import the API Keys page
const APIKeysPage = dynamic(() => import('./api-keys/page'), {
  loading: () => <div className="flex items-center justify-center py-8">Loading API Keys...</div>
})

function TabSync({ onTabChange }: { onTabChange: (tab: string) => void }) {
  const searchParams = useSearchParams()
  
  useEffect(() => {
    const tab = searchParams.get('tab')
    if (tab) {
      onTabChange(tab)
    }
  }, [searchParams, onTabChange])
  
  return null
}

export default function SettingsPageClient() {
  const [activeTab, setActiveTab] = useState('profile')

  return (
    <div className="min-h-screen bg-background pt-24 pb-12">
      <Suspense fallback={null}>
        <TabSync onTabChange={setActiveTab} />
      </Suspense>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">Settings</h1>
          <p className="text-muted-foreground">
            Manage your account, organization, and preferences
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 md:grid-cols-7 mb-8 bg-zinc-900/40">
            <TabsTrigger value="profile" className="flex items-center gap-2">
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">Profile</span>
            </TabsTrigger>
            <TabsTrigger value="organization" className="flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              <span className="hidden sm:inline">Organization</span>
            </TabsTrigger>
            <TabsTrigger value="api-keys" className="flex items-center gap-2">
              <Key className="w-4 h-4" />
              <span className="hidden sm:inline">API Keys</span>
            </TabsTrigger>
            <TabsTrigger value="routing" className="flex items-center gap-2">
              <Route className="w-4 h-4" />
              <span className="hidden sm:inline">Routing</span>
            </TabsTrigger>
            <TabsTrigger value="billing" className="flex items-center gap-2">
              <CreditCard className="w-4 h-4" />
              <span className="hidden sm:inline">Billing</span>
            </TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">Analytics</span>
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              <span className="hidden sm:inline">Security</span>
            </TabsTrigger>
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile" className="space-y-6">
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Profile Information</CardTitle>
                <CardDescription>Update your personal information</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="firstName">First Name</Label>
                    <Input id="firstName" placeholder="John" className="mt-1" />
                  </div>
                  <div>
                    <Label htmlFor="lastName">Last Name</Label>
                    <Input id="lastName" placeholder="Doe" className="mt-1" />
                  </div>
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" placeholder="john@example.com" className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="bio">Bio</Label>
                  <Input id="bio" placeholder="Tell us about yourself" className="mt-1" />
                </div>
                <Button className="bg-emerald-600 hover:bg-emerald-700 text-white">
                  Save Changes
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Organization Tab */}
          <TabsContent value="organization" className="space-y-6">
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Organization Details</CardTitle>
                <CardDescription>Manage your organization settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="orgName">Organization Name</Label>
                  <Input id="orgName" placeholder="Acme Inc." className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="orgSlug">Organization Slug</Label>
                  <Input id="orgSlug" placeholder="acme-inc" className="mt-1" />
                  <p className="text-xs text-muted-foreground mt-1">
                    Used in API endpoints and URLs
                  </p>
                </div>
                <div>
                  <Label htmlFor="orgDescription">Description</Label>
                  <Input id="orgDescription" placeholder="Brief description" className="mt-1" />
                </div>
                <Button className="bg-emerald-600 hover:bg-emerald-700 text-white">
                  Update Organization
                </Button>
              </CardContent>
            </Card>

            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Team Members</CardTitle>
                <CardDescription>Manage who has access to your organization</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-muted-foreground">
                  Team management coming soon
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* API Keys Tab */}
          <TabsContent value="api-keys">
            <APIKeysPage />
          </TabsContent>

          {/* Routing Tab */}
          <TabsContent value="routing" className="space-y-6">
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Routing Policies</CardTitle>
                <CardDescription>
                  Configure how Syntra routes queries to different providers
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-center py-8 text-muted-foreground">
                  <Route className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Routing policy configuration coming soon</p>
                  <p className="text-sm mt-2">
                    Configure provider preferences, fallback chains, and cost optimization rules
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Billing Tab */}
          <TabsContent value="billing" className="space-y-6">
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Usage & Billing</CardTitle>
                <CardDescription>Monitor your usage and manage billing</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground mb-1">This Month</div>
                    <div className="text-2xl font-bold">$0.00</div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground mb-1">Requests</div>
                    <div className="text-2xl font-bold">0</div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground mb-1">Tokens</div>
                    <div className="text-2xl font-bold">0</div>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-semibold text-foreground">Current Plan</h3>
                      <p className="text-sm text-muted-foreground">Starter Plan</p>
                    </div>
                    <Link href="/pricing">
                      <Button variant="outline">
                        Upgrade Plan
                        <ArrowRight className="ml-2 w-4 h-4" />
                      </Button>
                    </Link>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <h3 className="font-semibold text-foreground mb-4">Payment Method</h3>
                  <div className="text-center py-8 text-muted-foreground">
                    No payment method on file
                  </div>
                  <Button variant="outline">Add Payment Method</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-6">
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Usage Analytics</CardTitle>
                <CardDescription>Track your API usage and performance metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground mb-1">Total Requests</div>
                    <div className="text-2xl font-bold">0</div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground mb-1">Total Tokens</div>
                    <div className="text-2xl font-bold">0</div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground mb-1">Avg Response Time</div>
                    <div className="text-2xl font-bold">0ms</div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground mb-1">Active Keys</div>
                    <div className="text-2xl font-bold">0</div>
                  </div>
                </div>

                <div className="text-center py-8 text-muted-foreground">
                  <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Usage analytics coming soon</p>
                  <p className="text-sm mt-2">
                    Detailed insights into your API usage patterns and costs
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security" className="space-y-6">
            <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Security & Compliance</CardTitle>
                <CardDescription>Manage security settings and compliance</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h3 className="font-semibold text-foreground mb-4">Two-Factor Authentication</h3>
                  <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                    <div>
                      <div className="font-medium">2FA Status</div>
                      <div className="text-sm text-muted-foreground">Not enabled</div>
                    </div>
                    <Button variant="outline">Enable 2FA</Button>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <h3 className="font-semibold text-foreground mb-4">API Keys</h3>
                  <div className="text-center py-8 text-muted-foreground">
                    API key management
                  </div>
                  <Button variant="outline">Generate API Key</Button>
                </div>

                <div className="pt-4 border-t border-border">
                  <h3 className="font-semibold text-foreground mb-4">Audit Logs</h3>
                  <div className="text-center py-8 text-muted-foreground">
                    View security events and access logs
                  </div>
                  <Button variant="outline">View Logs</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
