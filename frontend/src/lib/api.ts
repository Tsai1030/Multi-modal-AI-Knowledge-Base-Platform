import axios from 'axios'
import { useAuthStore } from '@/store/authStore'
import type {
  DocumentListResponse,
  DocumentStatus,
  DocumentUploadResponse,
} from '@/types/document'
import type {
  LoginRequest,
  RoleUpdateRequest,
  SignupRequest,
  StatusUpdateRequest,
  TokenResponse,
  UserPublic,
} from '@/types/auth'
import type {
  ChatSession,
  SessionCreateRequest,
  SessionListResponse,
  SessionRenameRequest,
} from '@/types/session'
import type { SessionDetailResponse } from '@/types/message'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: false,
})

function normalizeDocumentsResponse(data: unknown): DocumentListResponse {
  if (Array.isArray(data)) {
    return {
      documents: data,
      total: data.length,
    }
  }

  if (
    data &&
    typeof data === 'object' &&
    'documents' in data &&
    Array.isArray((data as DocumentListResponse).documents)
  ) {
    const response = data as DocumentListResponse
    return {
      documents: response.documents,
      total: response.total ?? response.documents.length,
    }
  }

  return {
    documents: [],
    total: 0,
  }
}

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      await useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<TokenResponse>('/api/v1/auth/login', data).then((r) => r.data),

  signup: (data: SignupRequest) =>
    apiClient.post<UserPublic>('/api/v1/auth/signup', data).then((r) => r.data),

  me: () => apiClient.get<UserPublic>('/api/v1/auth/me').then((r) => r.data),
}

export const sessionApi = {
  list: (skip = 0, limit = 50) =>
    apiClient
      .get<SessionListResponse>('/api/v1/sessions/', { params: { skip, limit } })
      .then((r) => r.data),

  create: (data: SessionCreateRequest = {}) =>
    apiClient.post<ChatSession>('/api/v1/sessions/', data).then((r) => r.data),

  get: (sessionId: string) =>
    apiClient
      .get<SessionDetailResponse>(`/api/v1/sessions/${sessionId}`)
      .then((r) => r.data),

  rename: (sessionId: string, data: SessionRenameRequest) =>
    apiClient
      .patch<ChatSession>(`/api/v1/sessions/${sessionId}/title`, data)
      .then((r) => r.data),

  delete: (sessionId: string) => apiClient.delete(`/api/v1/sessions/${sessionId}`),
}

export const documentApi = {
  list: (skip = 0, limit = 50) =>
    apiClient
      .get('/api/v1/documents/', { params: { skip, limit } })
      .then((r) => normalizeDocumentsResponse(r.data)),

  upload: (file: File, sessionId?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (sessionId) {
      form.append('session_id', sessionId)
    }
    return apiClient
      .post<DocumentUploadResponse>('/api/v1/documents/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  getStatus: (docId: string) =>
    apiClient
      .get<{ id: string; status: DocumentStatus; error_message: string | null }>(
        `/api/v1/documents/${docId}/status`
      )
      .then((r) => r.data),

  delete: (docId: string) => apiClient.delete(`/api/v1/documents/${docId}`),
}

export const adminApi = {
  listUsers: () => apiClient.get<UserPublic[]>('/api/v1/admin/users').then((r) => r.data),

  updateRole: (userId: string, data: RoleUpdateRequest) =>
    apiClient.patch<UserPublic>(`/api/v1/admin/users/${userId}/role`, data).then((r) => r.data),

  updateStatus: (userId: string, data: StatusUpdateRequest) =>
    apiClient.patch<UserPublic>(`/api/v1/admin/users/${userId}/status`, data).then((r) => r.data),

  listAllDocuments: (skip = 0, limit = 100) =>
    apiClient
      .get('/api/v1/documents/', { params: { skip, limit } })
      .then((r) => normalizeDocumentsResponse(r.data)),
}
