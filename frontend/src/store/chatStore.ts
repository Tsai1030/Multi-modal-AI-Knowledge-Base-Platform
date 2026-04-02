import { create } from 'zustand'
import { sessionApi } from '@/lib/api'
import type { Message } from '@/types/message'
import type { ChatSession } from '@/types/session'

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
  setIsStreaming: (value: boolean) => void
}

export const useChatStore = create<ChatStore>((set) => ({
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
    set((state) => ({ sessions: [session, ...state.sessions] }))
    return session
  },

  selectSession: async (sessionId: string) => {
    set({ currentSessionId: sessionId })

    const detail = await sessionApi.get(sessionId)
    set((state) => {
      const hasSession = state.sessions.some((session) => session.id === detail.session.id)
      return {
        sessions: hasSession
          ? state.sessions.map((session) =>
              session.id === detail.session.id ? detail.session : session
            )
          : [detail.session, ...state.sessions],
        messages: {
          ...state.messages,
          [sessionId]: detail.messages,
        },
      }
    })
  },

  deleteSession: async (sessionId: string) => {
    await sessionApi.delete(sessionId)
    set((state) => ({
      sessions: state.sessions.filter((session) => session.id !== sessionId),
      currentSessionId:
        state.currentSessionId === sessionId ? null : state.currentSessionId,
      messages: Object.fromEntries(
        Object.entries(state.messages).filter(([id]) => id !== sessionId)
      ),
    }))
  },

  renameSession: async (sessionId: string, title: string) => {
    const updated = await sessionApi.rename(sessionId, { title })
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId ? updated : session
      ),
    }))
  },

  appendStreamToken: (token: string) =>
    set((state) => ({ streamingContent: state.streamingContent + token })),

  finalizeStreamMessage: (msg: Message, sessionId: string) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: [...(state.messages[sessionId] ?? []), msg],
      },
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              message_count: session.message_count + 1,
              last_message_at: msg.created_at,
            }
          : session
      ),
    })),

  clearStreamingContent: () => set({ streamingContent: '' }),

  setIsStreaming: (value: boolean) => set({ isStreaming: value }),
}))
