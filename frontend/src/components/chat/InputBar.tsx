'use client'

import { useRef, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface InputBarProps {
  onSubmit: (question: string) => void
  isStreaming: boolean
  queryMode: string
  disabled?: boolean
}

export function InputBar({ onSubmit, isStreaming, queryMode, disabled }: InputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = () => {
    const value = textareaRef.current?.value.trim()
    if (!value || isStreaming || disabled) return
    onSubmit(value)
    if (textareaRef.current) textareaRef.current.value = ''
  }

  return (
    <div className="border-t border-border bg-background px-4 py-3">
      <div className="relative flex items-end gap-2 rounded-xl border border-border bg-muted/30 px-3 py-2 focus-within:border-ring focus-within:ring-1 focus-within:ring-ring">
        <Textarea
          ref={textareaRef}
          placeholder="輸入訊息… (Enter 送出，Shift+Enter 換行)"
          onKeyDown={handleKeyDown}
          disabled={isStreaming || disabled}
          className={cn(
            'min-h-[40px] max-h-[160px] flex-1 resize-none border-0 bg-transparent p-0 shadow-none focus-visible:ring-0',
            'text-sm placeholder:text-muted-foreground/60'
          )}
          rows={1}
        />
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant="secondary" className="hidden text-xs sm:flex">
            {queryMode}
          </Badge>
          <Button
            size="sm"
            className="size-8 p-0"
            onClick={handleSend}
            disabled={isStreaming || disabled}
          >
            <Send className="size-4" />
          </Button>
        </div>
      </div>
      <p className="mt-1.5 text-center text-xs text-muted-foreground/50">
        AI 回應可能有誤，請自行判斷
      </p>
    </div>
  )
}
