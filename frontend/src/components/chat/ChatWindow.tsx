'use client'

import { useCallback, useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { Spinner } from '@/components/ui/spinner'
import { useSSEStream } from '@/hooks/useSSEStream'
import { useChatStore } from '@/store/chatStore'
import type { Message } from '@/types/message'
import { InputBar } from './InputBar'
import { MessageBubble } from './MessageBubble'
import { StreamingText } from './StreamingText'

interface ChatWindowProps {
  sessionId: string
}

export function ChatWindow({ sessionId }: ChatWindowProps) {
  const {
    sessions,
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
  const currentSession = sessions.find((session) => session.id === sessionId)
  const queryMode = currentSession?.query_mode ?? 'hybrid'

  useEffect(() => {
    void selectSession(sessionId)
  }, [sessionId, selectSession])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [sessionMessages.length, streamingContent])

  const onToken = useCallback(
    (token: string) => appendStreamToken(token),
    [appendStreamToken]
  )

  const onDone = useCallback(
    (messageId: string, sources: string[]) => {
      const assistantMessage: Message = {
        id: messageId,
        session_id: sessionId,
        role: 'assistant',
        content: useChatStore.getState().streamingContent,
        is_compacted_summary: false,
        rag_sources: sources.length > 0 ? sources : null,
        query_mode: queryMode,
        created_at: new Date().toISOString(),
      }

      finalizeStreamMessage(assistantMessage, sessionId)
      clearStreamingContent()
      setIsStreaming(false)
    },
    [clearStreamingContent, finalizeStreamMessage, queryMode, sessionId, setIsStreaming]
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

      const userMessage: Message = {
        id: crypto.randomUUID(),
        session_id: sessionId,
        role: 'user',
        content: question,
        is_compacted_summary: false,
        rag_sources: null,
        query_mode: queryMode,
        created_at: new Date().toISOString(),
      }

      useChatStore.setState((state) => ({
        messages: {
          ...state.messages,
          [sessionId]: [...(state.messages[sessionId] ?? []), userMessage],
        },
      }))

      setIsStreaming(true)
      clearStreamingContent()
      await stream(sessionId, question, queryMode)
    },
    [clearStreamingContent, isStreaming, queryMode, sessionId, setIsStreaming, stream]
  )

  return (
    <div className="relative flex h-full flex-col">
      <span className="fixed inset-x-0 top-0 z-10 flex h-14 items-center bg-background px-14 text-sm font-semibold tracking-wide text-foreground md:absolute md:inset-x-auto md:left-4 md:top-4 md:h-auto md:bg-transparent md:px-0">
        Multi-modal AI
      </span>
      <div className="flex-1 overflow-y-auto px-4 py-6 pt-20 md:pt-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {sessionMessages.length === 0 && !isStreaming && (
            <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
              輸入你的問題，開始這段對話
            </div>
          )}

          {sessionMessages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

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
        sessionId={sessionId}
        onSubmit={handleSubmit}
        isStreaming={isStreaming}
        queryMode={queryMode}
      />
    </div>
  )
}
