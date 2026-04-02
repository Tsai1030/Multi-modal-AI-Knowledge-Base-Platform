'use client'

import { useState, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'
import type { SSEEvent } from '@/types/message'

interface UseSSEStreamOptions {
  onToken: (token: string) => void
  onDone: (messageId: string, sources: string[]) => void
  onError: (error: string) => void
}

export function useSSEStream({ onToken, onDone, onError }: UseSSEStreamOptions) {
  const [isStreaming, setIsStreaming] = useState(false)
  const { token } = useAuthStore()

  const stream = useCallback(
    async (sessionId: string, question: string, mode: string) => {
      const apiBase = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
      setIsStreaming(true)

      try {
        const response = await fetch(`${apiBase}/api/v1/query/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ session_id: sessionId, question, mode }),
        })

        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          onError(data.detail ?? `請求失敗 (${response.status})`)
          return
        }

        const reader = response.body?.getReader()
        if (!reader) {
          onError('無法建立串流連線')
          return
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const raw = line.slice(6).trim()
            if (raw === '[DONE]') break

            try {
              const event: SSEEvent = JSON.parse(raw)
              if (event.type === 'token' && event.content) {
                onToken(event.content)
              } else if (event.type === 'done') {
                onDone(event.message_id ?? '', event.sources ?? [])
              } else if (event.type === 'error' && event.content) {
                onError(event.content)
              }
            } catch {
              // skip malformed line
            }
          }
        }
      } catch (err) {
        onError(err instanceof Error ? err.message : '連線中斷')
      } finally {
        setIsStreaming(false)
      }
    },
    [token, onToken, onDone, onError]
  )

  return { stream, isStreaming }
}
