'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { ChevronDown, ChevronUp, BookOpen } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Message } from '@/types/message'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
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

      {/* Content */}
      <div className={cn('flex max-w-[80%] flex-col gap-1', isUser ? 'items-end' : 'items-start')}>
        {message.is_compacted_summary && (
          <Badge variant="secondary" className="mb-1 text-xs">
            📝 對話摘要
          </Badge>
        )}

        <div
          className={cn(
            'rounded-xl px-4 py-2.5 text-sm leading-relaxed',
            isUser
              ? 'bg-foreground text-background'
              : 'bg-muted text-foreground'
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

        {/* RAG sources */}
        {message.rag_sources && message.rag_sources.length > 0 && (
          <div className="mt-1 w-full">
            <Button
              variant="ghost"
              className="h-7 gap-1 px-2 text-xs text-muted-foreground"
              onClick={() => setSourcesOpen((v) => !v)}
            >
              <BookOpen className="size-3" />
              參考來源 ({message.rag_sources.length})
              {sourcesOpen ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
            </Button>
            {sourcesOpen && (
              <ul className="mt-1 flex flex-col gap-1 rounded-md border border-border bg-muted/50 p-2">
                {message.rag_sources.map((src, i) => (
                  <li key={i} className="truncate text-xs text-muted-foreground">
                    {i + 1}. {src}
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
