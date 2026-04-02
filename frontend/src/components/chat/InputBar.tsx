'use client'

import { useRef, useState } from 'react'
import type { ChangeEvent, KeyboardEvent } from 'react'
import { Paperclip, Send } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { documentApi } from '@/lib/api'
import { useChatStore } from '@/store/chatStore'
import { cn } from '@/lib/utils'

interface InputBarProps {
  sessionId: string
  onSubmit: (question: string) => void
  isStreaming: boolean
  queryMode: string
  disabled?: boolean
}

export function InputBar({
  sessionId,
  onSubmit,
  isStreaming,
  queryMode,
  disabled,
}: InputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isUploading, setIsUploading] = useState(false)
  const selectSession = useChatStore((state) => state.selectSession)

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  const handleSend = () => {
    const value = textareaRef.current?.value.trim()
    if (!value || isStreaming || disabled || isUploading) return
    onSubmit(value)
    if (textareaRef.current) {
      textareaRef.current.value = ''
    }
  }

  const waitForDocumentReady = async (docId: string, fileName: string) => {
    const maxAttempts = 40

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 3000))
      const status = await documentApi.getStatus(docId)

      if (status.status === 'completed') {
        toast.success(`${fileName} 已完成處理，現在可以直接在這個聊天室提問。`)
        return
      }

      if (status.status === 'failed') {
        throw new Error(status.error_message ?? '文件處理失敗')
      }
    }

    toast.message(`${fileName} 仍在處理中，你可以稍後再回來確認狀態。`)
  }

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''

    if (!file || isUploading || isStreaming || disabled) return

    setIsUploading(true)
    try {
      const uploaded = await documentApi.upload(file, sessionId)
      await selectSession(sessionId)
      toast.success(`${file.name} 已上傳，文件庫與此聊天視窗都會看到這份檔案。`)
      await waitForDocumentReady(uploaded.id, file.name)
    } catch (error) {
      const message = error instanceof Error ? error.message : '上傳檔案時發生錯誤'
      toast.error(message)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="border-t border-border bg-background px-4 py-3">
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
        accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.md,.txt,.jpg,.jpeg,.png"
      />
      <div className="relative flex items-end gap-2 rounded-xl border border-border bg-muted/30 px-3 py-2 focus-within:border-ring focus-within:ring-1 focus-within:ring-ring">
        <Textarea
          ref={textareaRef}
          placeholder="輸入問題，Enter 送出，Shift+Enter 換行"
          onKeyDown={handleKeyDown}
          disabled={isStreaming || disabled || isUploading}
          className={cn(
            'min-h-[40px] max-h-[160px] flex-1 resize-none border-0 bg-transparent p-0 shadow-none focus-visible:ring-0',
            'text-sm placeholder:text-muted-foreground/60'
          )}
          rows={1}
        />
        <div className="flex shrink-0 items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="size-8 p-0"
            onClick={() => fileInputRef.current?.click()}
            disabled={isStreaming || disabled || isUploading}
          >
            <Paperclip className="size-4" />
          </Button>
          <Badge variant="secondary" className="hidden text-xs uppercase sm:flex">
            {isUploading ? 'uploading' : queryMode}
          </Badge>
          <Button
            type="button"
            size="sm"
            className="size-8 p-0"
            onClick={handleSend}
            disabled={isStreaming || disabled || isUploading}
          >
            <Send className="size-4" />
          </Button>
        </div>
      </div>
      <p className="mt-1.5 text-center text-xs text-muted-foreground/50">
        支援 PDF、Office、Markdown、文字與圖片檔，上傳後完成索引即可在此對話引用。
      </p>
    </div>
  )
}
