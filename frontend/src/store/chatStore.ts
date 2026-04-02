import { create } from 'zustand'
import type { ChatSession } from '@/types/session'
import type { Message } from '@/types/message'
import { sessionApi } from '@/lib/api'

interface ChatStore {
  sessions: ChatSession[]
  currentSessionId: string | null
  messages: Record<string, Message[]>
  isStreaming: boolean
  streamingContent: string

  loadSessions: () => Promise<void>
  createSession: (mode?: string) => Promise<ChatSession>
  selectSession: (sessionId: string) => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>
  renameSession: (sessionId: string, title: string) => Promise<void>
  appendStreamToken: (token: string) => void
  finalizeStreamMessage: (msg: Message, sessionId: string) => void
  clearStreamingContent: () => void
  setIsStreaming: (v: boolean) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  messages: {},
  isStreaming: false,
  streamingContent: '',

  loadSessions: async () => {
    const data = await sessionApi.list()
    set({ sessions: data.sessions })
  },

  createSession: async (mode = 'hybrid') => {
    const session = await sessionApi.create({ query_mode: mode })
    set((s) => ({ sessions: [session, ...s.sessions] }))
    return session
  },

  selectSession: async (sessionId: string) => {
    set({ currentSessionId: sessionId })
    if (!get().messages[sessionId]) {
      const detail = await sessionApi.get(sessionId)
      set((s) => ({
        messages: { ...s.messages, [sessionId]: detail.messages },
      }))
    }
  },

  deleteSession: async (sessionId: string) => {
    await sessionApi.delete(sessionId)
    set((s) => ({
      sessions: s.sessions.filter((sess) => sess.id !== sessionId),
      currentSessionId: s.currentSessionId === sessionId ? null : s.currentSessionId,
      messages: Object.fromEntries(
        Object.entries(s.messages).filter(([id]) => id !== sessionId)
      ),
    }))
  },

  renameSession: async (sessionId: string, title: string) => {
    const updated = await sessionApi.rename(sessionId, { title })
    set((s) => ({
      sessions: s.sessions.map((sess) => (sess.id === sessionId ? updated : sess)),
    }))
  },

  appendStreamToken: (token: string) =>
    set((s) => ({ streamingContent: s.streamingContent + token })),

  finalizeStreamMessage: (msg: Message, sessionId: string) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [sessionId]: [...(s.messages[sessionId] ?? []), msg],
      },
      sessions: s.sessions.map((sess) =>
        sess.id === sessionId
          ? { ...sess, message_count: sess.message_count + 1, last_message_at: msg.created_at }
          : sess
      ),
    })),

  clearStreamingContent: () => set({ streamingContent: '' }),

  setIsStreaming: (v: boolean) => set({ isStreaming: v }),
}))
