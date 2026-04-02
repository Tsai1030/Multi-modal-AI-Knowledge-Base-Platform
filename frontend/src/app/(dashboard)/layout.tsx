'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { SessionSidebar } from '@/components/chat/SessionSidebar'
import { useAuthStore } from '@/store/authStore'
import { Spinner } from '@/components/ui/spinner'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, restoreFromServer } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    restoreFromServer()
  }, [restoreFromServer])

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace('/login')
    }
  }, [isLoading, user, router])

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner className="size-6 text-muted-foreground" />
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="flex h-full">
      <SessionSidebar />
      <main className="flex flex-1 flex-col overflow-hidden bg-background">{children}</main>
    </div>
  )
}
