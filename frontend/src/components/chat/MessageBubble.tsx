'use client'

import { useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { BookOpen, ChevronDown, ChevronUp, FileText, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Message } from '@/types/message'

interface MessageBubbleProps {
  message: Message
}

interface UploadMeta {
  document_id: string
  file_name: string
}

const DOCUMENT_UPLOAD_PREFIX = '[[document-upload]]'

function parseUploadMeta(content: string): UploadMeta | null {
  if (!content.startsWith(DOCUMENT_UPLOAD_PREFIX)) {
    return null
  }

  try {
    return JSON.parse(content.slice(DOCUMENT_UPLOAD_PREFIX.length)) as UploadMeta
  } catch {
    return null
  }
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const isUser = message.role === 'user'
  const uploadMeta = useMemo(() => parseUploadMeta(message.content), [message.content])
  const isUploadMessage = message.role === 'system' && uploadMeta !== null

  if (isUploadMessage && uploadMeta) {
    return (
      <div className="flex justify-center">
        <div className="w-full max-w-xl rounded-2xl border border-border/70 bg-card/80 px-4 py-3 shadow-sm backdrop-blur">
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-muted">
              <FileText className="size-4 text-foreground/70" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="truncate text-sm font-medium text-foreground">
                  {uploadMeta.file_name}
                </p>
                <Badge variant="secondary" className="rounded-full px-2.5 text-[11px]">
                  已加入此對話
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                檔案已同步到文件庫，完成索引後即可直接在這個聊天室提問。
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      <div
        className={cn(
          'flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium',
          isUser
            ? 'bg-foreground text-background'
            : 'border border-border bg-muted text-muted-foreground'
        )}
      >
        {isUser ? 'U' : 'AI'}
      </div>

      <div className={cn('flex max-w-[80%] flex-col gap-1', isUser ? 'items-end' : 'items-start')}>
        {message.is_compacted_summary && (
          <Badge variant="secondary" className="mb-1 gap-1 text-xs">
            <Sparkles className="size-3" />
            對話摘要
          </Badge>
        )}

        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
            isUser ? 'bg-foreground text-background' : 'bg-muted text-foreground'
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none dark:prose-invert prose-p:leading-relaxed prose-pre:bg-background/50">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {message.rag_sources && message.rag_sources.length > 0 && (
          <div className="mt-1 w-full">
            <Button
              variant="ghost"
              className="h-7 gap-1 px-2 text-xs text-muted-foreground"
              onClick={() => setSourcesOpen((value) => !value)}
            >
              <BookOpen className="size-3" />
              參考來源 ({message.rag_sources.length})
              {sourcesOpen ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
            </Button>
            {sourcesOpen && (
              <ul className="mt-1 flex flex-col gap-1 rounded-md border border-border bg-muted/50 p-2">
                {message.rag_sources.map((source, index) => (
                  <li key={`${source}-${index}`} className="truncate text-xs text-muted-foreground">
                    {index + 1}. {source}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
