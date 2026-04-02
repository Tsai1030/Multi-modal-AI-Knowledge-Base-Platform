export interface UserPublic {
  id: string
  email: string
  full_name: string
  role: 'user' | 'admin'
  is_active: boolean
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface SignupRequest {
  email: string
  password: string
  full_name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface RoleUpdateRequest {
  role: 'user' | 'admin'
}

export interface StatusUpdateRequest {
  is_active: boolean
}
