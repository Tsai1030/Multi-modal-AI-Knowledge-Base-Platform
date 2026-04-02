import { create } from 'zustand'
import type { UserPublic } from '@/types/auth'

interface AuthStore {
  user: UserPublic | null
  token: string | null
  isLoading: boolean

  setAuth: (user: UserPublic, token: string) => void
  logout: () => Promise<void>
  restoreFromServer: () => Promise<void>
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  isLoading: true,

  setAuth: (user, token) => set({ user, token }),

  logout: async () => {
    await fetch('/api/auth/token', { method: 'DELETE' })
    set({ user: null, token: null })
  },

  restoreFromServer: async () => {
    set({ isLoading: true })
    try {
      const res = await fetch('/api/auth/me', { cache: 'no-store' })
      const { user, token } = await res.json()
      set({ user: user ?? null, token: token ?? null })
    } catch {
      set({ user: null, token: null })
    } finally {
      set({ isLoading: false })
    }
  },
}))
