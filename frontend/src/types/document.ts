export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Document {
  id: string
  title: string
  original_filename: string
  file_size: number
  mime_type: string
  status: DocumentStatus
  error_message: string | null
  uploaded_by_id: string
  created_at: string
  updated_at: string
}

export interface DocumentListResponse {
  documents: Document[]
  total: number
}

export interface DocumentUploadResponse {
  id: string
  title: string
  status: DocumentStatus
  created_at: string
}
