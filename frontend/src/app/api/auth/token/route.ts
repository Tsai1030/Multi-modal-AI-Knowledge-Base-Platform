import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

const COOKIE_NAME = 'auth_token'
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7 // 7 days

// POST /api/auth/token — set httpOnly cookie after login
export async function POST(request: Request) {
  const { token } = await request.json()
  if (!token || typeof token !== 'string') {
    return NextResponse.json({ error: 'Invalid token' }, { status: 400 })
  }

  const cookieStore = await cookies()
  cookieStore.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: COOKIE_MAX_AGE,
    path: '/',
  })

  return NextResponse.json({ ok: true })
}

// DELETE /api/auth/token — clear cookie on logout
export async function DELETE() {
  const cookieStore = await cookies()
  cookieStore.delete(COOKIE_NAME)
  return NextResponse.json({ ok: true })
}
