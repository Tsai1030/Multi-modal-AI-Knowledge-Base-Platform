export interface ChatSession {
  id: string
  title: string
  query_mode: string
  message_count: number
  last_message_at: string | null
  is_compacted: boolean
  created_at: string
}

export interface SessionListResponse {
  sessions: ChatSession[]
  total: number
}

export interface SessionCreateRequest {
  query_mode?: string
}

export interface SessionRenameRequest {
  title: string
}
