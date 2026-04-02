import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const AUTH_COOKIE = 'auth_token'

const PUBLIC_PATHS = ['/login', '/signup']
const PROTECTED_PREFIX = ['/chat', '/documents', '/admin']

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const hasToken = request.cookies.has(AUTH_COOKIE)

  // Already logged in → redirect away from auth pages
  if (hasToken && PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.redirect(new URL('/chat', request.url))
  }

  // Not logged in → redirect to login for protected routes
  if (!hasToken && PROTECTED_PREFIX.some((p) => pathname.startsWith(p))) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('next', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Root redirect
  if (pathname === '/') {
    return NextResponse.redirect(
      new URL(hasToken ? '/chat' : '/landing', request.url)
    )
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
