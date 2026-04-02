'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { Compass, Database, Globe, MessageSquarePlus } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
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
        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <Card className="border-border/70 bg-card/90 shadow-[0_24px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur">
            <CardHeader className="gap-4">
              <div className="flex size-12 items-center justify-center rounded-2xl border border-border bg-muted">
                <Compass />
              </div>
              <div className="flex flex-col gap-2">
                <CardTitle className="text-2xl tracking-tight">開始一段新對話</CardTitle>
                <CardDescription className="max-w-2xl text-sm leading-6">
                  先建立對話 session，再進入 RAG 問答畫面。建立後即可直接提問、串流回覆，並保留聊天歷史。
                </CardDescription>
              </div>
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

          <Card className="border-border/70 bg-gradient-to-br from-muted/70 via-background to-background shadow-[0_24px_60px_-30px_rgba(15,23,42,0.35)]">
            <CardHeader>
              <CardTitle className="text-base">使用流程</CardTitle>
              <CardDescription>
                這一頁對齊 step 7 規劃，作為聊天首頁與建立入口。
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 text-sm text-muted-foreground">
              <div className="rounded-2xl border border-border/70 bg-background/80 p-4">
                1. 先選擇 query mode 建立對話。
              </div>
              <div className="rounded-2xl border border-border/70 bg-background/80 p-4">
                2. 進入 `/chat/[sessionId]` 後開始提問，訊息會自動存入 session。
              </div>
              <div className="rounded-2xl border border-border/70 bg-background/80 p-4">
                3. 左側 sidebar 可切換、重新命名與刪除對話。
              </div>
              <Button
                variant="outline"
                className="mt-2 justify-start"
                onClick={() => handleCreateSession('hybrid')}
                disabled={isPending}
              >
                <MessageSquarePlus data-icon="inline-start" />
                直接建立 Hybrid 對話
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
