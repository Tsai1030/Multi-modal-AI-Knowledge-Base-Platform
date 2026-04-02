import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

const COOKIE_NAME = 'auth_token'
const API_BASE =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  'http://localhost:8000'

// GET /api/auth/me — read httpOnly cookie, verify with FastAPI, return user + token
export async function GET() {
  const cookieStore = await cookies()
  const token = cookieStore.get(COOKIE_NAME)?.value

  if (!token) {
    return NextResponse.json({ user: null, token: null })
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })

    if (!res.ok) {
      // Token is invalid or expired — clear cookie
      const cookieStore2 = await cookies()
      cookieStore2.delete(COOKIE_NAME)
      return NextResponse.json({ user: null, token: null })
    }

    const user = await res.json()
    return NextResponse.json({ user, token })
  } catch {
    return NextResponse.json({ user: null, token: null })
  }
}
