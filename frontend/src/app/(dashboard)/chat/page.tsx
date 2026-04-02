'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { Database, Globe, MessageSquarePlus } from 'lucide-react'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useChatStore } from '@/store/chatStore'

const MODE_OPTIONS = [
  {
    value: 'hybrid',
    title: 'Hybrid',
    description: '同時結合知識庫與語意檢索，適合大多數問答。',
    icon: MessageSquarePlus,
  },
  {
    value: 'local',
    title: 'Local',
    description: '偏重局部文件片段，適合追問單一文件內容。',
    icon: Database,
  },
  {
    value: 'global',
    title: 'Global',
    description: '偏重全域脈絡，適合做摘要與跨文件整理。',
    icon: Globe,
  },
] as const

export default function ChatDefaultPage() {
  const router = useRouter()
  const createSession = useChatStore((state) => state.createSession)
  const [pendingMode, setPendingMode] = useState<string | null>(null)
  const [isPending, startTransition] = useTransition()

  const handleCreateSession = (mode: string) => {
    setPendingMode(mode)

    startTransition(async () => {
      try {
        const session = await createSession(mode)
        router.push(`/chat/${session.id}`)
      } catch {
        toast.error('建立對話失敗')
      } finally {
        setPendingMode(null)
      }
    })
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center px-6 py-10">
        <div className="grid gap-6">
          <Card className="border-border/70 bg-card/90 shadow-[0_24px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur">
            <CardHeader className="items-center pb-2 pt-8 text-center">
              <CardTitle className="text-3xl tracking-tight">開始一段新對話</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {MODE_OPTIONS.map((option) => {
                const Icon = option.icon
                const isLoading = isPending && pendingMode === option.value

                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleCreateSession(option.value)}
                    disabled={isPending}
                    className="flex items-start gap-4 rounded-2xl border border-border/70 bg-background/70 p-4 text-left transition hover:border-foreground/20 hover:bg-muted/60 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-border bg-muted">
                      <Icon />
                    </div>
                    <div className="flex flex-1 flex-col gap-1">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium">{option.title}</span>
                        <span className="text-xs text-muted-foreground">
                          {isLoading ? '建立中...' : '建立 session'}
                        </span>
                      </div>
                      <p className="text-sm leading-6 text-muted-foreground">
                        {option.description}
                      </p>
                    </div>
                  </button>
                )
              })}
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  )
}
