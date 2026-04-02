'use client'

import { useEffect, useRef, useCallback } from 'react'
import { toast } from 'sonner'
import { Spinner } from '@/components/ui/spinner'
import { MessageBubble } from './MessageBubble'
import { StreamingText } from './StreamingText'
import { InputBar } from './InputBar'
import { useChatStore } from '@/store/chatStore'
import { useSSEStream } from '@/hooks/useSSEStream'
import type { Message } from '@/types/message'

interface ChatWindowProps {
  sessionId: string
  queryMode: string
}

export function ChatWindow({ sessionId, queryMode }: ChatWindowProps) {
  const {
    messages,
    isStreaming,
    streamingContent,
    appendStreamToken,
    finalizeStreamMessage,
    clearStreamingContent,
    setIsStreaming,
    selectSession,
  } = useChatStore()

  const bottomRef = useRef<HTMLDivElement>(null)
  const sessionMessages = messages[sessionId] ?? []

  useEffect(() => {
    selectSession(sessionId)
  }, [sessionId, selectSession])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [sessionMessages, streamingContent])

  const onToken = useCallback(
    (token: string) => appendStreamToken(token),
    [appendStreamToken]
  )

  const onDone = useCallback(
    (messageId: string, sources: string[]) => {
      const assistantMsg: Message = {
        id: messageId,
        session_id: sessionId,
        role: 'assistant',
        content: useChatStore.getState().streamingContent,
        is_compacted_summary: false,
        rag_sources: sources.length > 0 ? sources : null,
        query_mode: queryMode,
        created_at: new Date().toISOString(),
      }
      finalizeStreamMessage(assistantMsg, sessionId)
      clearStreamingContent()
      setIsStreaming(false)
    },
    [sessionId, queryMode, finalizeStreamMessage, clearStreamingContent, setIsStreaming]
  )

  const onError = useCallback(
    (error: string) => {
      clearStreamingContent()
      setIsStreaming(false)
      toast.error(error)
    },
    [clearStreamingContent, setIsStreaming]
  )

  const { stream } = useSSEStream({ onToken, onDone, onError })

  const handleSubmit = useCallback(
    async (question: string) => {
      if (isStreaming) return

      // Optimistically add user message to UI
      const userMsg: Message = {
        id: crypto.randomUUID(),
        session_id: sessionId,
        role: 'user',
        content: question,
        is_compacted_summary: false,
        rag_sources: null,
        query_mode: queryMode,
        created_at: new Date().toISOString(),
      }
      useChatStore.setState((s) => ({
        messages: {
          ...s.messages,
          [sessionId]: [...(s.messages[sessionId] ?? []), userMsg],
        },
      }))

      setIsStreaming(true)
      clearStreamingContent()
      await stream(sessionId, question, queryMode)
    },
    [isStreaming, sessionId, queryMode, stream, setIsStreaming, clearStreamingContent]
  )

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {sessionMessages.length === 0 && !isStreaming && (
            <div className="flex h-64 items-center justify-center text-muted-foreground text-sm">
              輸入問題開始對話
            </div>
          )}

          {sessionMessages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {/* Streaming message */}
          {isStreaming && (
            <div className="flex gap-3">
              <div className="flex size-7 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-xs font-medium text-muted-foreground">
                AI
              </div>
              <div className="max-w-[80%] rounded-xl bg-muted px-4 py-2.5 text-sm">
                {streamingContent ? (
                  <StreamingText content={streamingContent} />
                ) : (
                  <Spinner className="size-4 text-muted-foreground" />
                )}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <InputBar
        onSubmit={handleSubmit}
        isStreaming={isStreaming}
        queryMode={queryMode}
      />
    </div>
  )
}
