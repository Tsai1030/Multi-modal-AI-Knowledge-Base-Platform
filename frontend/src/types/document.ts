export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Document {
  id: string
  title: string
  filename: string
  file_size: number
  file_type: string
  status: DocumentStatus
  uploaded_by_id: string
  created_at: string
  updated_at: string
}

export interface DocumentListResponse {
  documents: Document[]
  total: number
}
