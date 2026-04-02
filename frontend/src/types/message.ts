export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  is_compacted_summary: boolean
  rag_sources: string[] | null
  query_mode: string | null
  created_at: string
}

export interface SessionDetailResponse {
  session: import('./session').ChatSession
  messages: Message[]
}

export type SSEEventType = 'token' | 'done' | 'error' | 'sources'

export interface SSEEvent {
  type: SSEEventType
  content?: string
  sources?: string[]
  session_id?: string
  message_id?: string
}
